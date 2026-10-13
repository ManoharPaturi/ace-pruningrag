"""Revalidate unchanged extracted proposals under the corrected lexical policy."""

import argparse
import json
from collections import Counter
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.claim_extraction import extraction_tasks
from ace_pruningrag.constrained_claims import validate_constrained as frozen_validation
from ace_pruningrag.unicode_claims import validate_constrained as corrected_validation


def replay(root):
    trace = root / "runs/kaggle/cohort-output-v1/cohort-pilot/generated/predictions.jsonl"
    outputs = root / "runs/version1/constrained-output-v1/constrained-pilot/extractions.jsonl"
    proof = read_json(root / "results/version1/constrained_verification.json")
    if (
        proof["status"] != "constrained_spans_decode_and_costs_reconstructed"
        or proof["trace_sha256"] != sha256_file(outputs)
        or proof["source_trace_sha256"] != sha256_file(trace)
    ):
        raise ValueError("verified unchanged constrained outputs required")
    tasks = extraction_tasks([json.loads(line) for line in trace.read_text().splitlines()])
    records = [json.loads(line) for line in outputs.read_text().splitlines()]
    if len(tasks) != len(records):
        raise ValueError("Unicode replay source coverage differs")
    changed, counts = [], Counter()
    for task, record in zip(tasks, records, strict=True):
        if task["task_sha256"] != record["task_sha256"]:
            raise ValueError("Unicode replay identity differs")
        original = frozen_validation(task, record["raw_proposal"])
        if original != record["validation"]:
            raise ValueError("frozen policy does not reconstruct original proposal")
        revised = corrected_validation(task, record["raw_proposal"])
        counts[revised["status"]] += 1
        if revised != original:
            changed.append(
                {
                    "task_sha256": task["task_sha256"],
                    "kind": task["kind"],
                    "interaction_id": task["interaction_id"],
                    "evidence_id": task.get("evidence_id"),
                    "original_status": original["status"],
                    "revised_status": revised["status"],
                    "revised_issues": revised["issues"],
                }
            )
    return {
        "scope": "Corrected-policy replay of unchanged old outputs; no new generation",
        "tasks": len(tasks),
        "revised_validation_counts": dict(counts),
        "changed_records": changed,
        "source_trace_sha256": sha256_file(trace),
        "extraction_trace_sha256": sha256_file(outputs),
        "frozen_policy_sha256": sha256_file(root / "src/ace_pruningrag/constrained_claims.py"),
        "corrected_policy_sha256": sha256_file(root / "src/ace_pruningrag/unicode_claims.py"),
        "actual_new_model_calls": 0,
        "old_outputs_modified": False,
        "neural_regeneration_verified": False,
        "semantic_role_improvement_established": False,
        "answer_acceptance_enabled": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)
    write_json(a.output, replay(Path.cwd()))
