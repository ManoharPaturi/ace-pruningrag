"""Bind exact-match review reuse and fresh changed-output AI assessments."""

import argparse
import json
import runpy
from collections import Counter
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.claim_extraction import digest, extraction_tasks


def verify(root):
    source = root / "runs/kaggle/cohort-output-v1/cohort-pilot/generated/predictions.jsonl"
    output = root / "runs/version1/unicode-output-v2/unicode-pilot/extractions.jsonl"
    proof_path = root / "results/version1/unicode_verification.json"
    proof = read_json(proof_path)
    reconstruct = runpy.run_path(str(root / "scripts/verify_unicode_extraction.py"))["verify"]
    if proof != reconstruct(root, root / "runs/version1/unicode-kernel-v2", output.parent, source):
        raise ValueError("Unicode execution proof differs from fresh reconstruction")
    comparison_path = root / "results/version1/unicode_control_comparison.json"
    compare = runpy.run_path(str(root / "scripts/compare_unicode_control.py"))["compare"]
    comparison = compare(root, output.parent, proof_path)
    if comparison != read_json(comparison_path):
        raise ValueError("Unicode control comparison differs")
    old_verify = runpy.run_path(str(root / "scripts/verify_constrained_reviews.py"))["verify"]
    old_coverage = old_verify(root)
    if not old_coverage["full_semantic_review_complete"]:
        raise ValueError("complete task-bound v1 reviews required for exact-match reuse")
    old_progress_path = root / "results/version1/constrained_review_progress.json"
    old_progress = read_json(old_progress_path)
    old = {
        r["task_sha256"]: r
        for entry in old_progress["audit_batches"]
        for r in read_json(root / "runs/version1" / entry["name"])["records"]
    }
    fresh_path = root / "runs/version1/unicode-changed-ai-review-v2.json"
    batch = read_json(fresh_path)
    if (
        batch["source_trace_sha256"] != sha256_file(source)
        or batch["extraction_trace_sha256"] != sha256_file(output)
        or batch["independent_human_review"] is not False
    ):
        raise ValueError("fresh Unicode review trace or reviewer scope differs")
    fresh = {r["task_sha256"]: r for r in batch["records"]}
    changed = {r["task_sha256"] for r in comparison["changed_records"] if r["raw_proposal_changed"]}
    if set(fresh) != changed or len(fresh) != len(batch["records"]):
        raise ValueError("changed Unicode proposal coverage differs")
    tasks = extraction_tasks([json.loads(x) for x in source.read_text().splitlines()])
    outputs = [json.loads(x) for x in output.read_text().splitlines()]
    reviewed, reused, fresh_count = [], 0, 0
    for task, result in zip(tasks, outputs, strict=True):
        key = task["task_sha256"]
        if result["task_sha256"] != key:
            raise ValueError("Unicode output identity differs")
        record = fresh[key] if key in changed else old[key]
        if key in changed:
            fresh_count += 1
        else:
            reused += 1
        if (
            record["input_text"] != task["text"]
            or record["raw_proposal"] != result["raw_proposal"]
            or record["raw_proposal_sha256"] != digest(result["raw_proposal"])
            or record["kind"] != task["kind"]
            or record["interaction_id"] != task["interaction_id"]
            or record.get("evidence_id") != task.get("evidence_id")
            or record["full_requirement_coverage_verified"] is not False
            or record["eligible_for_answer_acceptance"] is not False
            or not record["rationale"].strip()
        ):
            raise ValueError("Unicode review input/output identity or scope differs")
        valid = result["validation"]["status"] == "constrained_span_proposal"
        if record["reviewer_type"] != ("AI" if valid else "deterministic_contract_validation"):
            raise ValueError("Unicode review validity/reviewer type differs")
        if task["kind"] == "source" and valid and record["external_truth_verified"] is not False:
            raise ValueError("Unicode AI review cannot establish external truth")
        reviewed.append(record)
    sources = [r for r in reviewed if r["kind"] == "source" and r["reviewer_type"] == "AI"]
    return {
        "scope": (
            "Complete task-bound qualitative AI role review; not independent factual evaluation"
        ),
        "records_bound": len(reviewed),
        "exact_input_and_proposal_reviews_reused": reused,
        "fresh_changed_proposal_reviews": fresh_count,
        "AI_reviewed_query_proposals": sum(r["kind"] == "query" for r in reviewed),
        "AI_reviewed_source_proposals": len(sources),
        "source_review_counts": dict(Counter(r["semantic_status"] for r in sources)),
        "unreviewed_tasks": len(tasks) - len(reviewed),
        "changed_proposal_reviews_complete": True,
        "source_trace_sha256": sha256_file(source),
        "extraction_trace_sha256": sha256_file(output),
        "execution_verification_sha256": sha256_file(proof_path),
        "control_comparison_sha256": sha256_file(comparison_path),
        "original_review_progress_sha256": sha256_file(old_progress_path),
        "fresh_review_batch_sha256": sha256_file(fresh_path),
        "independent_human_review": False,
        "semantic_role_improvement_established": False,
        "full_requirement_coverage_verified": False,
        "answer_acceptance_enabled": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)
    write_json(a.output, verify(Path.cwd()))
