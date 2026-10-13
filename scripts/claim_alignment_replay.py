"""Compare blinded span proposals per selected item; not semantic support scoring."""

import argparse
import ast
import base64
import json
import zlib
from collections import Counter
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.claim_alignment import compare_proposals
from ace_pruningrag.claim_extraction import extraction_tasks


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-trace", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--verification", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)
    verified = read_json(a.verification)
    if verified["status"] != "extraction_spans_decode_and_costs_reconstructed":
        raise ValueError("complete extraction verification required")
    if verified["source_trace_sha256"] != sha256_file(a.source_trace) or verified[
        "trace_sha256"
    ] != sha256_file(a.run / "extractions.jsonl"):
        raise ValueError("alignment input hashes differ from verified sources")
    rows = [json.loads(line) for line in a.source_trace.read_text().splitlines()]
    tasks = extraction_tasks(rows)
    tree = ast.parse((a.bundle / "bootstrap.py").read_text())
    assignment = next(
        n
        for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "PAYLOAD" for t in n.targets)
    )
    payload = json.loads(zlib.decompress(base64.b64decode(ast.literal_eval(assignment.value))))
    submitted = json.loads(payload["files"]["configs/extraction_tasks.json"])
    if submitted["tasks"] != tasks:
        raise ValueError("alignment tasks differ")
    extractions = [
        json.loads(line) for line in (a.run / "extractions.jsonl").read_text().splitlines()
    ]
    if len(extractions) != len(tasks):
        raise ValueError("alignment extraction coverage differs")
    lookup = {}
    for task, extraction in zip(tasks, extractions, strict=True):
        if task["task_sha256"] != extraction["task_sha256"]:
            raise ValueError("alignment extraction identity differs")
        lookup[(task["kind"], task["interaction_id"], task.get("evidence_id"))] = extraction
    comparisons = []
    for row in rows:
        q = lookup[("query", row["interaction_id"], None)]
        for evidence in row["selected"]:
            source = lookup[("source", row["interaction_id"], evidence["evidence_id"])]
            comparisons.append(
                {
                    "interaction_id": row["interaction_id"],
                    "policy": row["policy"],
                    "evidence_id": evidence["evidence_id"],
                    "query_task_sha256": q["task_sha256"],
                    "source_task_sha256": source["task_sha256"],
                    "comparison": compare_proposals(
                        q.get("validation", {}), source.get("validation", {})
                    ),
                }
            )
    write_json(
        a.output,
        {
            "scope": "Literal span-proposal alignment; not entailment or QA accuracy",
            "comparisons": comparisons,
            "comparison_count": len(comparisons),
            "status_counts": dict(Counter(c["comparison"]["status"] for c in comparisons)),
            "source_trace_sha256": sha256_file(a.source_trace),
            "extraction_trace_sha256": verified["trace_sha256"],
            "verification_sha256": sha256_file(a.verification),
            "alignment_implementation_sha256": sha256_file(
                Path("src/ace_pruningrag/claim_alignment.py")
            ),
            "actual_new_model_calls": 0,
            "answer_acceptance_enabled": False,
            "semantic_tuple_accuracy": None,
            "complete_claim_coverage": None,
        },
    )


if __name__ == "__main__":
    main()
