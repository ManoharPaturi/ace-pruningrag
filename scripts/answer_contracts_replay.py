"""Replay partial query contracts over hash-admitted traces, preserving outputs."""

import argparse
from collections import Counter
from pathlib import Path

from ace_pruningrag.answer_contracts import diagnose_contract
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
    admission = read_json(root / "configs/demo.json")
    runs = {}
    for name, run in store.runs.items():
        rows = []
        for (qid, policy), row in sorted(run["rows"].items()):
            diagnostic = diagnose_contract(
                row["query"], row["prediction"], [e["evidence_id"] for e in row["evidence"]]
            )
            rows.append({"interaction_id": qid, "policy": policy, **diagnostic})
        runs[name] = {
            "status": run["status"],
            "trace_sha256": admission["runs"][name]["sha256"],
            "responses": len(rows),
            "status_counts": dict(Counter(r["status"] for r in rows)),
            "finding_counts": dict(Counter(f["code"] for r in rows for f in r["findings"])),
            "diagnostics": rows,
        }
    write_json(
        args.output,
        {
            "scope": "Partial explicit query constraints; no semantic acceptance or quality score",
            "admission_sha256": sha256_file(root / "configs/demo.json"),
            "implementation_sha256": sha256_file(root / "src/ace_pruningrag/answer_contracts.py"),
            "form_implementation_sha256": sha256_file(root / "src/ace_pruningrag/answer_checks.py"),
            "runs": runs,
            "actual_new_llm_calls": 0,
            "generator_outputs_changed": False,
            "gold_or_human_labels_used": False,
            "limitations": [
                "Missing fields and unparsed answers remain unresolved, never accepted.",
                "Only literal dates/decades, opening/closing price and form checks are supported.",
                "Entity roles, units, semantic relations and source support are not established.",
                "Quoted/negated/comparison scopes are conservatively skipped, not resolved.",
                "This inspected development replay is not a held-out improvement measurement.",
            ],
        },
    )


if __name__ == "__main__":
    main()
