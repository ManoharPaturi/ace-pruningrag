"""Explicit prospective-cohort selector preparation; gold labels never enter selection."""

import hashlib
import json
import time
from itertools import combinations

from .artifacts import read_json, sha256_file
from .generation import messages
from .prospective import freeze
from .retrieval import bm25_rank, terms
from .selection import Candidate, SelectionProblem
from .selection_experiment import STOPWORDS

METHODS = ("top_k", "mmr", "coverage", "joint", "exact")


def load_cohort(root, output):
    protocol = read_json(root / "configs/cohort_evaluation.json")
    admitted = read_json(root / "results/evaluation/prospective_v1/manifest.json")
    if (
        protocol["scope"] != "prospective_selector_generation_v1"
        or protocol["packet_sha256"] != admitted["packet_sha256"]
        or protocol["query_ids"] != admitted["query_ids"]
        or protocol["methods"] != list(METHODS)
        or protocol["max_llm_calls"] != 250
    ):
        raise ValueError("explicit frozen cohort and five-selector contract required")
    frozen = freeze(root, output)
    if frozen["packet_sha256"] != protocol["packet_sha256"]:
        raise ValueError("reconstructed cohort differs from admitted packet")
    from .dataset import iter_records, verify_dataset

    config = read_json(root / protocol["generator_config"])
    for key in (
        "seed",
        "sampling",
        "candidate_limit",
        "chunk_words",
        "max_items",
        "total_tokens",
        "max_new_tokens",
    ):
        if protocol[key] != config[key]:
            raise ValueError("cohort generator settings must preserve the pinned control")
    dataset = verify_dataset(read_json(root / config["dataset_config"]), root)
    records = {
        r.interaction_id: r
        for r in iter_records(dataset)
        if r.interaction_id in protocol["query_ids"]
    }
    if set(records) != set(protocol["query_ids"]):
        raise ValueError("missing cohort questions")
    return protocol, config, [records[qid] for qid in protocol["query_ids"]]


def prepare_selectors(query, config, tokenize):
    from .evidence import web_chunks

    start = time.perf_counter()
    ranked = bm25_rank(query.query, web_chunks(query, config["chunk_words"]))[
        : config["candidate_limit"]
    ]
    retrieval_seconds = time.perf_counter() - start
    requirements = tuple(sorted(set(terms(query.query)) - STOPWORDS)) or ("__no_terms__",)
    maximum = max((score for _, score in ranked), default=0) or 1
    candidates = [
        Candidate(
            e.evidence_id,
            e.content,
            "web",
            e.source_url or f"page:{e.page_index}",
            score / maximum,
            tuple(float(term in set(terms(e.content))) for term in requirements),
        )
        for e, score in ranked
    ]
    term_sets = {c.evidence_id: set(terms(c.content)) for c in candidates}
    similarity = {}
    for a, b in combinations(candidates, 2):
        left, right = term_sets[a.evidence_id], term_sets[b.evidence_id]
        similarity[tuple(sorted((a.evidence_id, b.evidence_id)))] = len(left & right) / max(
            1, len(left | right)
        )
    evidence = {e.evidence_id: e.as_dict() for e, _ in ranked}
    cached = {}

    def cost(items):
        key = tuple(sorted(c.evidence_id for c in items))
        if key not in cached:
            cached[key] = (
                len(tokenize(messages(query, items, config["system_prompt"])))
                + config["max_new_tokens"]
            )
        return cached[key]

    # Retain the established development objective: no unvalidated semantic groups/conflicts.
    problem = SelectionProblem(
        candidates,
        requirements,
        (),
        similarity,
        {},
        cost,
        config["total_tokens"],
        config["max_items"],
    )
    result = {}
    for method in METHODS:
        selected_start = time.perf_counter()
        selected = problem.select(method)
        msg = messages(query, selected, config["system_prompt"])
        ids = tokenize(msg)
        if len(ids) + config["max_new_tokens"] > config["total_tokens"]:
            raise ValueError("full request exceeds token cap")
        result[method] = {
            "messages": msg,
            "input_ids": ids,
            "selected": [evidence[c.evidence_id] for c in selected],
            "candidate_ids": [c.evidence_id for c in candidates],
            "proxy_requirements": list(requirements),
            "groups": [],
            "conflicts": [],
            "objective": problem.objective(selected),
            "prompt_sha256": hashlib.sha256(
                json.dumps(msg, ensure_ascii=False).encode()
            ).hexdigest(),
            "selection_seconds": time.perf_counter() - selected_start,
        }
    return result, {
        "shared_web_retrieval_calls": 1,
        "shared_retrieval_seconds": retrieval_seconds,
        "cost_cache_entries": len(cached),
    }


def source_hashes(root):
    return {
        str(p.relative_to(root)): sha256_file(p)
        for p in sorted((root / "src/ace_pruningrag").glob("*.py"))
    }
