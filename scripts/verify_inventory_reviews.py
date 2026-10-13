"""Bind qualitative review of valid inventories without hiding rejected outputs."""

import argparse
import json
import runpy
from collections import Counter
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.claim_extraction import digest, extraction_tasks


def verify(root):
    source = root / "runs/kaggle/cohort-output-v1/cohort-pilot/generated/predictions.jsonl"
    run = root / "runs/version1/inventory-output-v1/inventory-pilot"
    proof_path = root / "results/version1/inventory_verification.json"
    audit_path = root / "results/version1/inventory_structural_audit.json"
    audit_fn = runpy.run_path(str(root / "scripts/audit_inventory_extraction.py"))["audit"]
    if read_json(audit_path) != audit_fn(
        root, root / "runs/version1/inventory-kernel-v1", run, source, proof_path
    ):
        raise ValueError("inventory structural audit differs from fresh reconstruction")
    tasks = extraction_tasks([json.loads(x) for x in source.read_text().splitlines()])
    outputs = [json.loads(x) for x in (run / "extractions.jsonl").read_text().splitlines()]
    valid = {
        t["task_sha256"]: (t, r)
        for t, r in zip(tasks, outputs, strict=True)
        if r["validation"]["status"] == "bound_inventory_proposal"
    }
    batch_path = root / "runs/version1/inventory-valid-ai-review-v1.json"
    batch = read_json(batch_path)
    if batch["source_trace_sha256"] != sha256_file(source) or batch[
        "extraction_trace_sha256"
    ] != sha256_file(run / "extractions.jsonl"):
        raise ValueError("inventory review trace hashes differ")
    seen = set()
    for record in batch["records"]:
        key = record["task_sha256"]
        if key in seen or key not in valid:
            raise ValueError("duplicate or nonvalid inventory review identity")
        seen.add(key)
        task, output = valid[key]
        if (
            record["input_text"] != task["text"]
            or record["raw_proposal"] != output["raw_proposal"]
            or record["raw_proposal_sha256"] != digest(output["raw_proposal"])
            or record["interaction_id"] != task["interaction_id"]
            or record["kind"] != task["kind"]
            or record.get("evidence_id") != task.get("evidence_id")
            or record["reviewer_type"] != "AI"
            or any(
                record[k] is not False
                for k in (
                    "independent_human_review",
                    "full_requirement_coverage_verified",
                    "eligible_for_answer_acceptance",
                    "external_truth_verified",
                )
            )
            or not isinstance(record["rationale"], str)
            or not record["rationale"].strip()
        ):
            raise ValueError("inventory review binding or scope differs")
    if seen != set(valid):
        raise ValueError("valid inventory review coverage incomplete")
    return {
        "scope": "Qualitative AI role review of all valid inventories; rejected roles unassessed",
        "total_tasks": len(tasks),
        "structurally_valid_inventories": len(valid),
        "AI_reviewed_valid_inventories": len(seen),
        "valid_inventory_review_complete": True,
        "query_reviews": sum(r["kind"] == "query" for r in batch["records"]),
        "source_reviews": sum(r["kind"] == "source" for r in batch["records"]),
        "semantic_categories": dict(Counter(r["semantic_status"] for r in batch["records"])),
        "rejected_inventories_without_full_semantic_review": len(tasks) - len(valid),
        "full_semantic_review_complete": False,
        "source_trace_sha256": sha256_file(source),
        "extraction_trace_sha256": sha256_file(run / "extractions.jsonl"),
        "execution_verification_sha256": sha256_file(proof_path),
        "structural_audit_sha256": sha256_file(audit_path),
        "AI_review_batch_sha256": sha256_file(batch_path),
        "independent_human_review": False,
        "full_requirement_coverage_verified": False,
        "answer_acceptance_enabled": False,
        "semantic_role_improvement_established": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)
    write_json(a.output, verify(Path.cwd()))
