"""Bind partial AI role review to exact constrained inputs and proposals."""

import argparse
import json
from collections import Counter
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file
from ace_pruningrag.claim_extraction import digest, extraction_tasks


def verify(root):
    progress = read_json(root / "results/version1/constrained_review_progress.json")
    trace = root / "runs/kaggle/cohort-output-v1/cohort-pilot/generated/predictions.jsonl"
    outputs_path = root / "runs/version1/constrained-output-v1/constrained-pilot/extractions.jsonl"
    verification = root / "results/version1/constrained_verification.json"
    if (
        progress["source_trace_sha256"] != sha256_file(trace)
        or progress["extraction_trace_sha256"] != sha256_file(outputs_path)
        or progress["verification_sha256"] != sha256_file(verification)
    ):
        raise ValueError("constrained review source hashes differ")
    tasks = extraction_tasks([json.loads(line) for line in trace.read_text().splitlines()])
    outputs = [json.loads(line) for line in outputs_path.read_text().splitlines()]
    if len(tasks) != len(outputs):
        raise ValueError("constrained review source coverage differs")
    lookup = {t["task_sha256"]: (t, output) for t, output in zip(tasks, outputs, strict=True)}
    seen, records = set(), []
    for entry in progress["audit_batches"]:
        if Path(entry["name"]).name != entry["name"]:
            raise ValueError("unsafe constrained audit path")
        path = root / "runs/version1" / entry["name"]
        if sha256_file(path) != entry["sha256"]:
            raise ValueError("constrained audit batch hash differs")
        batch = read_json(path)
        if (
            batch["source_trace_sha256"] != sha256_file(trace)
            or batch["extraction_trace_sha256"] != sha256_file(outputs_path)
            or batch["independent_human_review"] is not False
            or len(batch["records"]) != entry["records"]
        ):
            raise ValueError("constrained audit scope differs")
        for r in batch["records"]:
            key = r["task_sha256"]
            if key in seen or key not in lookup:
                raise ValueError("duplicate or foreign constrained review")
            seen.add(key)
            task, output = lookup[key]
            if (
                output["task_sha256"] != key
                or r["input_text"] != task["text"]
                or r["raw_proposal"] != output["raw_proposal"]
                or r["raw_proposal_sha256"] != digest(output["raw_proposal"])
                or r["interaction_id"] != task["interaction_id"]
                or r["kind"] != task["kind"]
                or r.get("evidence_id") != task.get("evidence_id")
                or r["eligible_for_answer_acceptance"] is not False
                or r["full_requirement_coverage_verified"] is not False
                or not isinstance(r.get("rationale"), str)
                or not r["rationale"].strip()
            ):
                raise ValueError("constrained review identity/content/acceptance binding differs")
            valid = output["validation"]["status"] == "constrained_span_proposal"
            if r["reviewer_type"] != ("AI" if valid else "deterministic_contract_validation"):
                raise ValueError("constrained reviewer scope differs")
            records.append(r)
    query = [r for r in records if r["kind"] == "query"]
    reviewed_sources = [r for r in records if r["kind"] == "source" and r["reviewer_type"] == "AI"]
    failed = [r for r in records if r["reviewer_type"] == "deterministic_contract_validation"]
    valid_sources = sum(
        t["kind"] == "source" and o["validation"]["status"] == "constrained_span_proposal"
        for t, o in zip(tasks, outputs, strict=True)
    )
    expected = {
        "total_tasks": len(tasks),
        "AI_reviewed_query_proposals": len(query),
        "AI_reviewed_source_proposals": len(reviewed_sources),
        "structural_failure_assessments": len(failed),
        "unreviewed_source_proposals": valid_sources - len(reviewed_sources),
        "query_review_counts": dict(Counter(r["semantic_status"] for r in query)),
        "full_semantic_review_complete": len(seen) == len(tasks),
        "independent_human_review": False,
        "answer_acceptance_enabled": False,
    }
    if any(progress.get(k) != value for k, value in expected.items()):
        raise ValueError("constrained review counts or scope differ from bound records")
    return {"records_bound": len(records), **expected}


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(verify(Path.cwd())))
