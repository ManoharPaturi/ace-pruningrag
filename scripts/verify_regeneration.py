"""Reconstruct actual retry eligibility, prompts, source rows, outputs and costs."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from transformers import AutoTokenizer
from verify_generated import verify

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.daily_prices import DailyPrices
from ace_pruningrag.dataset import QueryInput, iter_records, verify_dataset
from ace_pruningrag.generation import prepare_context
from ace_pruningrag.historical_comparison import historical_source
from ace_pruningrag.historical_prices import prior_close_request
from ace_pruningrag.regeneration import _inventory
from ace_pruningrag.reliability import PriceClaim, sufficient, verify_price_answer


def verify_retry(root, run):
    baseline = verify(root, run / "generated")
    retries = run / "regenerated"
    manifest = read_json(retries / "manifest.json")
    protocol = read_json(root / "configs/bounded_regeneration.json")
    assert manifest["protocol_sha256"] == sha256_file(root / "configs/bounded_regeneration.json")
    assert manifest["initial_trace_sha256"] == sha256_file(run / "generated/predictions.jsonl")
    for name, key in (("predictions", "trace_sha256"), ("decisions", "decisions_sha256")):
        assert sha256_file(retries / f"{name}.jsonl") == manifest[key]
    initial = [
        json.loads(x) for x in (run / "generated/predictions.jsonl").read_text().splitlines()
    ]
    later = [json.loads(x) for x in (retries / "predictions.jsonl").read_text().splitlines()]
    decisions = [json.loads(x) for x in (retries / "decisions.jsonl").read_text().splitlines()]
    config = read_json(root / "configs/historical_routing.json")
    prices = DailyPrices(read_json(root / "configs/crag_prices.json"), root)
    snapshot = sha256_file(prices.path)
    assert manifest["snapshot_sha256"] == snapshot
    queries = {
        r.interaction_id: r.inference_input()
        for r in iter_records(verify_dataset(read_json(root / config["dataset_config"]), root))
        if r.interaction_id in config["query_ids"]
    }
    inventory = _inventory(prices)
    tokenizer = AutoTokenizer.from_pretrained(
        root / config["generator"]["directory"], local_files_only=True
    )

    def tokenize(msg):
        return tokenizer.apply_chat_template(msg, tokenize=True, add_generation_prompt=True)

    def claims(evidence):
        return tuple(
            PriceClaim(e["ticker"], e["requested_date"], e["close"], e["source_ref"])
            for e in evidence
            if e["source_kind"] == "api"
        )

    mapping = {(r["interaction_id"], r["policy"]): r for r in later}
    assert len(mapping) == len(later)
    wanted = set()
    expected_decisions = []
    for row in initial:
        q = QueryInput(row["interaction_id"], row["query"], row["query_time"], ())
        request = prior_close_request(q, inventory)
        assert request is not None
        original_claims = claims(row["selected"])
        needs = not sufficient(request, original_claims)
        before = verify_price_answer(row["prediction"], request, original_claims)
        after, prediction = before, row["prediction"]
        if needs:
            key = (q.interaction_id, row["policy"])
            wanted.add(key)
            retry = mapping[key]
            # Full search results are recovered from pinned dataset, not cached generated output.
            original = queries[q.interaction_id]
            caps, fetch = historical_source(original, prices, snapshot)
            prepared = prepare_context(original, config, "all_available", tokenize, caps, fetch)
            assert retry["retry_policy"] == protocol["retry_policy"] == "all_available"
            assert retry["selected"] == prepared["evidence"]
            assert retry["plan"] == json.loads(json.dumps(prepared["plan"]))
            assert retry["candidate_ids"] == prepared["candidate_ids"]
            assert (
                retry["actual_source_calls"] == prepared["source_calls"] == {"web": 1, "finance": 1}
            )
            assert (
                retry["prompt_sha256"]
                == hashlib.sha256(
                    json.dumps(prepared["messages"], ensure_ascii=False).encode()
                ).hexdigest()
            )
            assert retry["input_tokens"] == len(prepared["input_ids"])
            assert retry["output_tokens"] == len(retry["output_ids"]) <= 96
            assert (
                retry["prediction"]
                == tokenizer.decode(retry["output_ids"], skip_special_tokens=True).strip()
            )
            combined = row["input_tokens"] + retry["input_tokens"] + 192
            assert retry["combined_reserved_tokens"] == combined <= 4096
            assert retry["input_tokens"] + 96 <= 2048
            assert retry["actual_llm_calls"] == 1
            prediction = retry["prediction"]
            after = verify_price_answer(prediction, request, claims(retry["selected"]))
        expected_decisions.append(
            {
                "interaction_id": q.interaction_id,
                "policy": row["policy"],
                "before_verdict": before,
                "after_verdict": after,
                "retried": needs,
                "final_prediction": prediction,
                "released_answer": prediction
                if after == "supported_price_field"
                else "I don't know.",
            }
        )
    assert wanted == set(mapping) and len(later) == 8
    assert decisions == expected_decisions
    summary = read_json(retries / "summary.json")
    assert summary["protocol"] == protocol
    assert summary["initial_llm_calls"] == 18
    assert (
        summary["extra_llm_calls"]
        == summary["extra_web_calls"]
        == summary["extra_finance_calls"]
        == 8
    )
    assert summary["total_llm_calls"] == 26
    assert summary["extra_validation_price_reads"] == 8
    assert summary["inventory_reads"] == 26
    assert summary["total_input_tokens"] == sum(r["input_tokens"] for r in initial + later)
    assert summary["total_output_tokens"] == sum(r["output_tokens"] for r in initial + later)
    assert summary["maximum_combined_reserved_tokens"] == max(
        r["combined_reserved_tokens"] for r in later
    )
    for policy in config["policies"]:
        group = [r for r in decisions if r["policy"] == policy]
        reported = summary["per_policy"][policy]
        assert reported["requests"] == 6
        assert reported["retries"] == sum(r["retried"] for r in group)
        for key in ("before", "after"):
            assert reported[f"{key}_verdicts"] == dict(Counter(r[f"{key}_verdict"] for r in group))
    assert summary["extra_generation_seconds"] == sum(r["generation_seconds"] for r in later)
    assert read_json(run / "environment_isolation.json")["base_preserved"] is True
    recovered_bundle = read_json(run / "bundle_manifest.json")
    for name, digest in recovered_bundle.items():
        assert sha256_file(root / name) == digest
    assert read_json(run / "completion.json")["actual_llm_calls"] == 26
    return {
        "status": "independently_verified",
        "initial": baseline,
        "retries": 8,
        "total_llm_calls": 26,
        "maximum_combined_reserved_tokens": summary["maximum_combined_reserved_tokens"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    write_json(args.output, verify_retry(Path.cwd(), args.run))
