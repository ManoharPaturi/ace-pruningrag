"""Phase 4 gold-free replay or CI preparation check using original dated SQLite."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.daily_prices import DailyPrices
from ace_pruningrag.dataset import iter_records, verify_dataset
from ace_pruningrag.historical_comparison import historical_source
from ace_pruningrag.historical_prices import prior_close_request
from ace_pruningrag.reliability import (
    PriceClaim,
    bounded_retrieve,
    sufficient,
    verify_price_answer,
)


def run(input_path: Path, output: Path):
    if output.exists():
        raise FileExistsError(output)
    root = Path.cwd()
    config = read_json(root / "configs/historical_routing.json")
    prices_config = read_json(root / "configs/crag_prices.json")
    prices = DailyPrices(prices_config, root)
    snapshot = prices_config["assets"][0]["sha256"]
    queries = {
        r.interaction_id: r.inference_input()
        for r in iter_records(verify_dataset(read_json(root / config["dataset_config"]), root))
        if r.interaction_id in config["query_ids"]
    }
    rows = [json.loads(line) for line in input_path.read_text().splitlines()]
    expected = {(qid, p) for qid in config["query_ids"] for p in config["policies"]}
    if len(rows) != 18 or {(r["interaction_id"], r["policy"]) for r in rows} != expected:
        raise ValueError("exactly the frozen 18 unique pairs are required")
    generated = all("prediction" in r for r in rows)
    if any("prediction" in r for r in rows) != generated:
        raise ValueError("mixed preparation/prediction inputs")
    if generated:
        manifest = read_json(input_path.parent / "manifest.json")
        if manifest["config"] != config or manifest["trace_sha256"] != sha256_file(input_path):
            raise ValueError("frozen trace/config binding failed")
    sources = {}
    for qid, query in queries.items():
        _, fetch = historical_source(query, prices, snapshot)
        evidence = fetch()
        request = prior_close_request(query, {evidence["ticker"]})
        if request is None:
            raise ValueError("request invalid")
        sources[qid] = (request, evidence, fetch)
    outputs = []
    for row in rows:
        request, original, fetch = sources[row["interaction_id"]]

        def make_claim(evidence, original=original):
            # Do not trust cached traces or the annotation audit as source truth.
            if any(evidence.get(k) != value for k, value in original.items()):
                raise ValueError("selected structured evidence differs from original SQLite row")
            return PriceClaim(
                evidence["ticker"],
                evidence["requested_date"],
                evidence["close"],
                evidence["source_ref"],
            )

        initial = tuple(make_claim(e) for e in row["selected"] if e["source_kind"] == "api")
        for variant, retry, conflict in (
            ("verify_only", False, True),
            ("retry_without_conflict_guard", True, False),
            ("retry_and_verify", True, True),
        ):
            claims, calls = bounded_retrieve(
                request,
                initial,
                lambda fetch=fetch, make_claim=make_claim: (make_claim(fetch()),),
                int(retry),
            )
            verdict = (
                verify_price_answer(row["prediction"], request, claims, conflict)
                if generated
                else "preparation_only"
            )
            outputs.append(
                {
                    "interaction_id": row["interaction_id"],
                    "policy": row["policy"],
                    "variant": variant,
                    "extra_api_calls": calls,
                    "sufficient_dated_price": sufficient(request, claims),
                    "verdict": verdict,
                    "released_answer": (
                        row["prediction"] if verdict == "supported_price_field" else "I don't know."
                    )
                    if generated
                    else None,
                }
            )
    groups = defaultdict(list)
    for row in outputs:
        groups[(row["variant"], row["policy"])].append(row)
    summary = {
        "scope": "Phase 4 historical development replay; no new model generation or human labels",
        "input_sha256": sha256_file(input_path),
        "snapshot_sha256": snapshot,
        "method_sha256": {
            name: sha256_file(root / name)
            for name in (
                "src/ace_pruningrag/reliability.py",
                "src/ace_pruningrag/historical_prices.py",
                "scripts/reliability_replay.py",
            )
        },
        "questions": 6,
        "original_requests": 18,
        "variants": 3,
        "actual_new_llm_calls": 0,
        "actual_judge_calls": 0,
        "shared_validation_price_reads": 12,
        "shared_inventory_reads": 6,
        "max_extra_api_calls_per_request_per_variant": 1,
        "max_evidence_rounds": 2,
        "actual_replay_extra_api_calls": sum(r["extra_api_calls"] for r in outputs),
        "input_predictions_present": generated,
        "per_variant_policy": [
            {
                "variant": v,
                "policy": p,
                "requests": len(items),
                "sufficient_dated_price": sum(r["sufficient_dated_price"] for r in items),
                "extra_api_calls": sum(r["extra_api_calls"] for r in items),
                "verdicts": dict(Counter(r["verdict"] for r in items)),
                "released_answers": sum(r["verdict"] == "supported_price_field" for r in items),
                "withheld_answers": sum(r["verdict"] != "supported_price_field" for r in items)
                if generated
                else None,
            }
            for (v, p), items in sorted(groups.items())
        ],
        "human_semantic_review_complete": False,
        "full_phase4_research_gate_passed": False,
        "limitations": [
            "Six previously inspected development questions, not a held-out evaluation.",
            "Web prose is unparsed, not asserted conflict-free or unsupported.",
            "Retry adds verifier evidence only; it does not regenerate or improve model answers.",
            "Currency and adjustment basis unknown; currency prose fails closed.",
            "A supported price field is not an independent semantic correctness label.",
            "Conflict ablation requires controlled tests: no natural comparable conflict here.",
        ],
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "decisions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in outputs))
    summary["decisions_sha256"] = sha256_file(output / "decisions.jsonl")
    write_json(output / "summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.input, args.output)
