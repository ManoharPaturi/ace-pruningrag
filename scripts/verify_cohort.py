"""Reconstruct every cohort request and verify raw spans, token IDs, decisions and costs."""

import argparse
import hashlib
import json
from pathlib import Path

from transformers import AutoTokenizer

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.cohort import METHODS, prepare_selectors
from ace_pruningrag.dataset import iter_records, verify_dataset


def verify(root, run):
    manifest = read_json(run / "manifest.json")
    protocol = read_json(root / "configs/cohort_evaluation.json")
    config = read_json(root / protocol["generator_config"])
    assert manifest["protocol"] == protocol
    assert manifest["generator_config"] == config
    assert manifest["protocol_sha256"] == sha256_file(root / "configs/cohort_evaluation.json")
    assert manifest["trace_sha256"] == sha256_file(run / "predictions.jsonl")
    assert manifest["retrieval_costs_sha256"] == sha256_file(run / "retrieval_costs.json")
    assert (
        protocol["query_ids"]
        == read_json(root / "results/evaluation/prospective_v1/manifest.json")["query_ids"]
    )
    assert sha256_file(run / "cohort/packet.json") == protocol["packet_sha256"]
    for name, digest in manifest["source_sha256"].items():
        assert sha256_file(root / name) == digest
    records = {
        r.interaction_id: r
        for r in iter_records(verify_dataset(read_json(root / config["dataset_config"]), root))
        if r.interaction_id in protocol["query_ids"]
    }
    rows = [json.loads(x) for x in (run / "predictions.jsonl").read_text().splitlines()]
    wanted = {(qid, m) for qid in protocol["query_ids"] for m in METHODS}
    assert len(rows) == len(wanted) == 250
    assert {(r["interaction_id"], r["policy"]) for r in rows} == wanted
    tokenizer = AutoTokenizer.from_pretrained(
        root / config["generator"]["directory"], local_files_only=True, trust_remote_code=False
    )
    maximum = 0
    for index, qid in enumerate(protocol["query_ids"]):
        record = records[qid]
        q = record.inference_input()
        prepared, _ = prepare_selectors(
            q,
            config,
            lambda m: tokenizer.apply_chat_template(m, tokenize=True, add_generation_prompt=True),
        )
        expected_order = list(METHODS[index % 5 :] + METHODS[: index % 5])
        group = [r for r in rows if r["interaction_id"] == qid]
        assert [r["policy"] for r in group] == expected_order
        for r in group:
            p = prepared[r["policy"]]
            assert r["query"] == q.query and r["query_time"] == q.query_time
            assert r["execution_order"] == expected_order
            for key in (
                "candidate_ids",
                "selected",
                "proxy_requirements",
                "groups",
                "conflicts",
                "objective",
                "prompt_sha256",
            ):
                assert r[key] == p[key]
            assert r["input_tokens"] == len(p["input_ids"])
            assert r["output_tokens"] == len(r["output_ids"]) <= 96
            assert r["input_tokens"] + 96 <= 2048
            assert (
                r["prediction"]
                == tokenizer.decode(r["output_ids"], skip_special_tokens=True).strip()
            )
            assert r["actual_llm_calls"] == 1
            assert r["generation_seconds"] >= 0 and r["selection_seconds"] >= 0
            assert (
                r["prompt_sha256"]
                == hashlib.sha256(
                    json.dumps(p["messages"], ensure_ascii=False).encode()
                ).hexdigest()
            )
            for e in r["selected"]:
                page = q.search_results[e["page_index"]]
                assert e["source_url"] == page["page_url"]
                assert e["content"] == page[e["field"]][e["char_start"] : e["char_end"]]
                assert e["interaction_id"] == qid
            normalized = r["prediction"].strip().casefold()
            exact = normalized in {a.strip().casefold() for a in record.answers}
            abstained = normalized in (
                "i don't know",
                "i don't know.",
                "i do not know",
                "i do not know.",
            )
            outcome = (
                "abstained"
                if abstained
                else "exact_agreement"
                if exact
                else "needs_semantic_review"
            )
            assert r["evaluation"] == {
                "exact_agreement": exact,
                "abstained": abstained,
                "outcome": outcome,
            }
            maximum = max(maximum, r["input_tokens"] + 96)
        print(f"Verified {index + 1}/50", flush=True)
    summary = read_json(run / "summary.json")
    assert summary["actual_llm_calls"] == 250
    assert summary["queries"] == summary["shared_candidate_retrievals"] == 50
    assert summary["input_tokens"] == sum(r["input_tokens"] for r in rows)
    assert summary["output_tokens"] == sum(r["output_tokens"] for r in rows)
    assert summary["maximum_reserved_tokens"] == maximum
    costs = read_json(run / "retrieval_costs.json")
    assert [r["interaction_id"] for r in costs] == protocol["query_ids"]
    assert all(r["shared_web_retrieval_calls"] == 1 for r in costs)
    for m in METHODS:
        group = [r for r in rows if r["policy"] == m]
        assert summary["per_method"][m] == {
            "answers": 50,
            "literal_matches": sum(r["evaluation"]["exact_agreement"] for r in group),
            "abstentions": sum(r["evaluation"]["abstained"] for r in group),
        }
    assert read_json(run.parent / "environment_isolation.json")["base_preserved"] is True
    assert read_json(run.parent / "completion.json")["actual_llm_calls"] == 250
    return {
        "status": "cohort_outputs_verified",
        "questions": 50,
        "answers": 250,
        "maximum_reserved_tokens": maximum,
        "human_review_complete": False,
        "evidence_completeness": None,
        "semantic_accuracy": None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    write_json(args.output, verify(Path.cwd(), args.run))
