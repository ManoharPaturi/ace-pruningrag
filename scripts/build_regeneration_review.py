"""Bind the last actual generation for each policy/query to a readable review packet."""

import argparse
import json
from pathlib import Path

from build_generated_review import build

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.dataset import iter_records, verify_dataset
from ace_pruningrag.generation import evaluate_answer

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    root = Path.cwd()
    initial_path = args.run / "generated/predictions.jsonl"
    retry_path = args.run / "regenerated/predictions.jsonl"
    manifest = read_json(args.run / "regenerated/manifest.json")
    assert sha256_file(initial_path) == manifest["initial_trace_sha256"]
    assert sha256_file(retry_path) == manifest["trace_sha256"]
    initial = [json.loads(x) for x in initial_path.read_text().splitlines()]
    retry = {
        (r["interaction_id"], r["policy"]): r
        for r in (json.loads(x) for x in retry_path.read_text().splitlines())
    }
    config = read_json(root / "configs/historical_routing.json")
    records = {
        r.interaction_id: r
        for r in iter_records(verify_dataset(read_json(root / config["dataset_config"]), root))
        if r.interaction_id in config["query_ids"]
    }
    final = []
    for original in initial:
        key = (original["interaction_id"], original["policy"])
        row = dict(original)
        if key in retry:
            row.update(retry[key])
        row["regeneration_round"] = 2 if key in retry else 1
        row["evaluation"] = evaluate_answer(
            row["prediction"], records[row["interaction_id"]].answers
        )
        final.append(row)
    args.output.mkdir(parents=True, exist_ok=False)
    trace = args.output / "predictions.jsonl"
    trace.write_text("".join(json.dumps(r) + "\n" for r in final))
    write_json(
        args.output / "manifest.json",
        {
            "scope": "Last actual generation, before conservative verifier filtering",
            "initial_trace_sha256": sha256_file(initial_path),
            "retry_trace_sha256": sha256_file(retry_path),
            "trace_sha256": sha256_file(trace),
            "answers": len(final),
        },
    )
    print(build(args.output, args.output / "review.html"))
