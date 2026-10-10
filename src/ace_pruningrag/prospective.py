"""Gold-free prospective sampling and provenance-bound human evidence review."""

import hashlib
import re
from collections import Counter
from urllib.parse import urlsplit

from .artifacts import read_json, sha256_file, write_json
from .dataset import iter_records, verify_dataset
from .evidence import web_chunks
from .retrieval import bm25_rank


def canonical_url(value):
    parsed = urlsplit(value.strip())
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None
    host = parsed.hostname.casefold().removeprefix("www.")
    # Preserve query parameters: they may identify a different article/entity.
    return host + parsed.path.rstrip("/") + ("?" + parsed.query if parsed.query else "")


def question_key(query):
    return " ".join(re.findall(r"\w+", query.casefold()))


def exposed_ids(value):
    result = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ("interaction_id", "query_id") and isinstance(item, str):
                result.add(item)
            elif key == "query_ids" and isinstance(item, list):
                result.update(x for x in item if isinstance(x, str))
            else:
                result.update(exposed_ids(item))
    elif isinstance(value, list):
        for item in value:
            result.update(exposed_ids(item))
    return result


def sample_queries(queries, excluded, seed, size):
    """Exclude prior IDs/questions/source pages and source overlap within the new set."""
    by_id = {q.interaction_id: q for q in queries}
    if not excluded <= set(by_id):
        raise ValueError("exposure ledger contains IDs outside the pinned dataset")
    urls = {canonical_url(p["page_url"]) for qid in excluded for p in by_id[qid].search_results} - {
        None
    }
    texts = {question_key(by_id[qid].query) for qid in excluded}
    chosen, rejected = [], Counter()
    order = sorted(
        queries, key=lambda q: hashlib.sha256(f"{seed}\0{q.interaction_id}".encode()).hexdigest()
    )
    for q in order:
        if q.interaction_id in excluded:
            rejected["prior_question"] += 1
            continue
        keys = {canonical_url(p["page_url"]) for p in q.search_results} - {None}
        if not keys:
            rejected["no_canonical_source"] += 1
            continue
        if question_key(q.query) in texts:
            rejected["duplicate_question_text"] += 1
            continue
        if keys & urls:
            rejected["shared_source_page"] += 1
            continue
        if not any(p["page_result"].strip() or p["page_snippet"].strip() for p in q.search_results):
            rejected["empty_source_text"] += 1
            continue
        chosen.append(q)
        urls.update(keys)
        texts.add(question_key(q.query))
        if len(chosen) == size:
            break
    if len(chosen) != size:
        raise ValueError("not enough source-disjoint prospective questions")
    return chosen, dict(rejected)


def freeze(root, output):
    if output.exists():
        raise FileExistsError(output)
    config_path = root / "configs/prospective_evaluation.json"
    config = read_json(config_path)
    if (
        config["scope"] != "prospective_web_candidate_evidence_review"
        or config["sample_size"] != 50
        or config["exclude_shared_canonical_urls"] is not True
        or config["exclude_duplicate_normalized_questions"] is not True
    ):
        raise ValueError("only the frozen source-disjoint prospective protocol is allowed")
    dataset_config = read_json(root / config["dataset_config"])
    dataset = verify_dataset(dataset_config, root)
    queries = [r.inference_input() for r in iter_records(dataset)]
    ledger, excluded = {}, set()
    for name in config["exposure_sources"]:
        path = root / name
        ledger[name] = sha256_file(path)
        excluded.update(exposed_ids(read_json(path)))
    chosen, rejected = sample_queries(queries, excluded, config["seed"], config["sample_size"])
    packet = {
        "scope": config["scope"],
        "config": config,
        "dataset_sha256": sha256_file(dataset),
        "exposure_sources_sha256": ledger,
        "excluded_query_ids": sorted(excluded),
        "questions": [
            {
                "interaction_id": q.interaction_id,
                "query": q.query,
                "query_time": q.query_time,
                "pages": list(q.search_results),
                "candidates": [
                    e.as_dict()
                    for e, _ in bm25_rank(q.query, web_chunks(q, config["chunk_words"]))[
                        : config["candidate_limit"]
                    ]
                ],
            }
            for q in chosen
        ],
    }
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "packet.json", packet)
    summary = {
        "scope": config["scope"],
        "dataset_sha256": packet["dataset_sha256"],
        "config_sha256": sha256_file(config_path),
        "method_sha256": {
            name: sha256_file(root / name)
            for name in (
                "src/ace_pruningrag/prospective.py",
                "src/ace_pruningrag/retrieval.py",
                "src/ace_pruningrag/evidence.py",
            )
        },
        "exposure_sources_sha256": ledger,
        "excluded_query_ids": sorted(excluded),
        "query_ids": [q.interaction_id for q in chosen],
        "questions": len(chosen),
        "exposure_questions": len(excluded),
        "rejections_before_sample_filled": rejected,
        "packet_sha256": sha256_file(output / "packet.json"),
        "candidate_spans": sum(len(q["candidates"]) for q in packet["questions"]),
        "actual_llm_calls": 0,
        "human_review_complete": False,
        "publication_evaluation_ready": False,
        "limitations": [
            "Prospective to documented pilots; this is not an independently sealed test set.",
            "URL/text disjointness does not establish complete entity/event disjointness.",
            "Source availability sampling is not representative of all RM3QA questions.",
            "Web candidate support labels cannot establish cross-source necessity.",
            "No correctness or supporting-evidence labels have been manufactured.",
        ],
    }
    write_json(output / "manifest.json", summary)
    return summary


def validate_packet(packet, root):
    config = read_json(root / "configs/prospective_evaluation.json")
    if packet["config"] != config:
        raise ValueError("packet differs from frozen configuration")
    dataset = verify_dataset(read_json(root / config["dataset_config"]), root)
    if sha256_file(dataset) != packet["dataset_sha256"]:
        raise ValueError("packet dataset binding differs")
    queries = [r.inference_input() for r in iter_records(dataset)]
    excluded = set()
    if set(packet["exposure_sources_sha256"]) != set(config["exposure_sources"]):
        raise ValueError("exposure ledger incomplete")
    for name, digest in packet["exposure_sources_sha256"].items():
        if sha256_file(root / name) != digest:
            raise ValueError("exposure source changed")
        excluded.update(exposed_ids(read_json(root / name)))
    if sorted(excluded) != packet["excluded_query_ids"]:
        raise ValueError("excluded IDs altered")
    chosen, _ = sample_queries(queries, excluded, config["seed"], config["sample_size"])
    if len(packet["questions"]) != len(chosen):
        raise ValueError("packet question count differs")
    for q, row in zip(chosen, packet["questions"], strict=True):
        expected = {
            "interaction_id": q.interaction_id,
            "query": q.query,
            "query_time": q.query_time,
            "pages": list(q.search_results),
            "candidates": [
                e.as_dict()
                for e, _ in bm25_rank(q.query, web_chunks(q, config["chunk_words"]))[
                    : config["candidate_limit"]
                ]
            ],
        }
        if row != expected:
            raise ValueError("packet question, source or candidate span differs")


def validate_decisions(export, packet, packet_sha256):
    if export.get("artifact_type") != "human_candidate_evidence_review":
        raise ValueError("unexpected annotation type")
    if export.get("packet_sha256") != packet_sha256:
        raise ValueError("review bound to a different packet")
    if not isinstance(export.get("reviewer"), str) or not export["reviewer"].strip():
        raise ValueError("reviewer identity required")
    lookup = {q["interaction_id"]: q for q in packet["questions"]}
    reviews = export.get("reviews")
    if not isinstance(reviews, list) or not reviews:
        raise ValueError("nonempty reviews required")
    seen = set()
    for r in reviews:
        qid = r.get("interaction_id")
        if qid not in lookup or qid in seen:
            raise ValueError("unknown or duplicate reviewed question")
        seen.add(qid)
        if r.get("status") not in ("pending", "reviewed", "needs_changes"):
            raise ValueError("invalid status")
        if r.get("answerability") not in (
            "pending",
            "supported_by_candidates",
            "missing_evidence",
            "uncertain",
        ):
            raise ValueError("invalid answerability")
        if type(r.get("attested")) is not bool or not all(
            isinstance(r.get(k), str) for k in ("requirements", "notes")
        ):
            raise ValueError("attestation and text fields required")
        sets = r.get("acceptable_sets")
        if not isinstance(sets, list):
            raise ValueError("acceptable sets must be an array")
        ids = {e["evidence_id"] for e in lookup[qid]["candidates"]}
        for group in sets:
            if (
                not isinstance(group, list)
                or not group
                or any(not isinstance(item, str) for item in group)
                or len(set(group)) != len(group)
                or not set(group) <= ids
            ):
                raise ValueError("acceptable set contains duplicate, empty or unknown evidence")
        if len({tuple(sorted(g)) for g in sets}) != len(sets):
            raise ValueError("duplicate acceptable support set")
        if r["status"] == "reviewed":
            if (
                not r["attested"]
                or not r["requirements"].strip()
                or r["answerability"] in ("pending", "uncertain")
            ):
                raise ValueError("reviewed decision requires resolved attested requirements")
            if (r["answerability"] == "supported_by_candidates") != bool(sets):
                raise ValueError("support sets contradict answerability")
    complete = seen == set(lookup) and all(r["status"] == "reviewed" for r in reviews)
    return {
        "status": "prospective_review_validated",
        "review_records": len(reviews),
        "questions": len(lookup),
        "complete_human_candidate_review": complete,
        "decisions": dict(Counter(r["status"] for r in reviews)),
        "answerability": dict(Counter(r["answerability"] for r in reviews)),
        "unresolved_questions": len(lookup) - sum(r["status"] == "reviewed" for r in reviews),
        "independent_semantic_accuracy_available": False,
        "cross_source_necessity_established": False,
        "publication_evaluation_ready": False,
    }
