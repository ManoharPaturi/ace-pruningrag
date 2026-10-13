"""Real movie/web candidate integration with source fidelity and pinned-tokenizer budgets."""

import argparse
import json
from pathlib import Path

from transformers import AutoTokenizer

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.claim_extraction import digest
from ace_pruningrag.dataset import iter_records, verify_dataset
from ace_pruningrag.movie_evidence import retrieve_movie_evidence
from ace_pruningrag.movie_search import MovieNameSearch
from ace_pruningrag.movie_snapshot import MovieSnapshot
from ace_pruningrag.source_controls import prepare_source_controls


def smoke(root, records_manifest=None, names_manifest=None):
    config = read_json(root / "configs/generated_pilot.json")
    probes = read_json(root / "configs/movie_evidence_probe.json")
    dataset = verify_dataset(read_json(root / config["dataset_config"]), root)
    ids = {p["interaction_id"] for p in probes["queries"]}
    records = {
        r.interaction_id: r.inference_input()
        for r in iter_records(dataset)
        if r.interaction_id in ids
    }
    if set(records) != ids or len(ids) != len(probes["queries"]):
        raise ValueError("movie development probe query coverage differs")
    movie_config = read_json(root / "configs/crag_movie.json")
    snapshot = MovieSnapshot(
        movie_config,
        root,
        root / "data/crag/movie/snapshot.sqlite",
        read_json(records_manifest or root / "results/phase1/movie_index.json")["index_sha256"],
    )
    search = MovieNameSearch(
        snapshot,
        root / "data/crag/movie/names.sqlite",
        read_json(names_manifest or root / "results/phase1/movie_name_index.json")[
            "search_index_sha256"
        ],
    )
    tokenizer = AutoTokenizer.from_pretrained(
        root / config["generator"]["directory"], local_files_only=True, trust_remote_code=False
    )

    def tokenize(messages):
        return tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)

    results = []
    for probe in probes["queries"]:
        query = records[probe["interaction_id"]]
        api, lookup = retrieve_movie_evidence(query, probe["requests"], search, movie_config)
        # Compare each canonical value to its own verified record, never another name-search hit.
        with snapshot.connection() as db:
            for item in api:
                binding = lookup["provenance"][item.evidence_id]
                name, payload = db.execute(
                    "SELECT name,payload FROM records WHERE rowid=? AND kind=?",
                    (binding["source_rowid"], binding["entity_kind"]),
                ).fetchone()
                record = json.loads(payload)
                content = json.loads(item.content)
                if (
                    content
                    != {
                        "entity_kind": binding["entity_kind"],
                        "source_name": name,
                        "record_id": record.get("id"),
                        "field": binding["record_field"],
                        "value": record[binding["record_field"]],
                    }
                    or digest(record) != binding["record_sha256"]
                    or digest(content["value"]) != binding["field_value_sha256"]
                    or digest(item.content) != binding["canonical_content_sha256"]
                ):
                    raise ValueError("movie canonical field or provenance differs from source")
        requests, shared = prepare_source_controls(query, api, config, tokenize)
        results.append(
            {
                "interaction_id": query.interaction_id,
                "query_sha256": digest(query.query),
                "lookup": lookup,
                "shared_pool": shared,
                "controls": {
                    key: {
                        k: v
                        for k, v in request.items()
                        if k not in ("messages", "input_ids", "selected")
                    }
                    | {
                        "input_tokens": len(request["input_ids"]),
                        "selected_ids": [e["evidence_id"] for e in request["selected"]],
                        "selected_source_kinds": [e["source_kind"] for e in request["selected"]],
                    }
                    for key, request in requests.items()
                },
                "all_api_fields_source_verified": True,
                "actual_answer_generation_calls": 0,
                "semantic_identity_verified": False,
                "semantic_support_verified": False,
            }
        )
    return {
        "scope": probes["scope"],
        "status": "movie_web_candidate_fidelity_and_budget_smoke_complete",
        "probe_config_sha256": sha256_file(root / "configs/movie_evidence_probe.json"),
        "generator_config_sha256": sha256_file(root / "configs/generated_pilot.json"),
        "generator_revision": config["generator"]["revision"],
        "queries": len(results),
        "control_requests_prepared": sum(len(r["controls"]) for r in results),
        "actual_movie_source_calls": sum(r["lookup"]["source_calls"] for r in results),
        "shared_retrieval_is_standalone_latency_benchmark": False,
        "actual_answer_generation_calls": 0,
        "answer_acceptance_enabled": False,
        "cross_source_benefit_established": False,
        "independent_human_review": False,
        "records": results,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--records-manifest", type=Path)
    p.add_argument("--names-manifest", type=Path)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    write_json(args.output, smoke(Path.cwd(), args.records_manifest, args.names_manifest))
