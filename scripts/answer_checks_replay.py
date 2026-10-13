"""Replay query-only form checks over admitted traces; no correction or model calls."""

import argparse
from collections import Counter
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.demo import DemoStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    root = Path.cwd()
    store = DemoStore(root)
    runs = {}
    admission = read_json(root / "configs/demo.json")
    for name, run in store.runs.items():
        rows = list(run["rows"].values())
        counts = Counter(issue for r in rows for issue in r["answer_form_checks"]["issues"])
        runs[name] = {
            "status": run["status"],
            "trace_sha256": admission["runs"][name]["sha256"],
            "responses": len(rows),
            "issue_counts": dict(counts),
            "flagged_responses": sum(bool(r["answer_form_checks"]["issues"]) for r in rows),
            "explicit_rectangle_calculations": sum(
                r["answer_form_checks"]["calculation"] is not None for r in rows
            ),
        }
    write_json(
        args.output,
        {
            "scope": "Post-hoc form diagnostics; not semantic improvement or claim verification",
            "admission_sha256": sha256_file(root / "configs/demo.json"),
            "runs": runs,
            "actual_new_llm_calls": 0,
            "generator_outputs_changed": False,
            "gold_or_human_labels_used": False,
            "limitations": [
                "List checks parse numbered lines only; unparsed lists remain unresolved.",
                "Geometry and compatible units must be explicit before calculating.",
                "No form issue detected does not prove correctness or source support.",
                "This inspected development replay is not a held-out ablation.",
            ],
        },
    )


if __name__ == "__main__":
    main()
