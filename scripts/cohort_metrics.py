"""Paired literal-agreement/abstention diagnostics; no inferred semantic labels."""

import argparse
import json
import random
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.cohort import METHODS


def paired_interval(deltas, samples=10000, seed=42):
    if not deltas or samples < 1:
        raise ValueError("nonempty paired query differences and positive resamples required")
    rng = random.Random(seed)
    n = len(deltas)
    values = sorted(sum(deltas[rng.randrange(n)] for _ in range(n)) / n for _ in range(samples))
    return {
        "mean_difference": sum(deltas) / n,
        "bootstrap_95_percentile_interval": [
            values[int((samples - 1) * 0.025)],
            values[int((samples - 1) * 0.975)],
        ],
        "resamples": samples,
        "seed": seed,
    }


def summarize(run):
    manifest = read_json(run / "manifest.json")
    assert sha256_file(run / "predictions.jsonl") == manifest["trace_sha256"]
    rows = [json.loads(x) for x in (run / "predictions.jsonl").read_text().splitlines()]
    ids = manifest["protocol"]["query_ids"]
    lookup = {(r["interaction_id"], r["policy"]): r for r in rows}
    wanted = {(qid, m) for qid in ids for m in METHODS}
    if len(lookup) != len(rows) or set(lookup) != wanted:
        raise ValueError("complete unique frozen method/query pairs required")
    report = {
        "scope": "Exploratory paired literal agreement and abstention, not semantic accuracy",
        "questions": len(ids),
        "responses": len(rows),
        "comparison_control": "top_k",
        "multiple_comparison_adjustment": None,
        "per_method": {},
        "paired_differences": {},
        "limitations": [
            "Question-level resampling does not establish entity/event independence.",
            "Unparsed or nonmatching answers are not classified incorrect.",
            "Intervals are exploratory and not evidence of cross-source efficacy.",
        ],
    }
    for method in METHODS:
        group = [lookup[(qid, method)] for qid in ids]
        report["per_method"][method] = {
            "literal_agreement_fraction": sum(r["evaluation"]["exact_agreement"] for r in group)
            / len(ids),
            "abstention_fraction": sum(r["evaluation"]["abstained"] for r in group) / len(ids),
            "input_tokens": sum(r["input_tokens"] for r in group),
            "output_tokens": sum(r["output_tokens"] for r in group),
            "generation_seconds": sum(r["generation_seconds"] for r in group),
            "actual_llm_calls": len(group),
            "semantic_accuracy": None,
        }
        if method != "top_k":
            report["paired_differences"][method] = {
                metric: paired_interval(
                    [
                        int(lookup[(qid, method)]["evaluation"][key])
                        - int(lookup[(qid, "top_k")]["evaluation"][key])
                        for qid in ids
                    ]
                )
                for metric, key in (
                    ("literal_agreement", "exact_agreement"),
                    ("abstention", "abstained"),
                )
            }
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    write_json(args.output, summarize(args.run))
