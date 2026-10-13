"""Revalidate complete structural/AI audit bindings; not human review or truth."""

import argparse
import json
from collections import Counter
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file
from ace_pruningrag.claim_extraction import digest, extraction_tasks, validate_proposal


def verify(trace, extractions, audit, verification, report):
    v = read_json(verification)
    if v["trace_sha256"] != sha256_file(extractions) or v["source_trace_sha256"] != sha256_file(
        trace
    ):
        raise ValueError("extraction verification bindings differ")
    if v["status"] != "extraction_spans_decode_and_costs_reconstructed":
        raise ValueError("complete extraction verification required")
    tasks = extraction_tasks([json.loads(line) for line in trace.read_text().splitlines()])
    outputs = [json.loads(line) for line in extractions.read_text().splitlines()]
    private = read_json(audit)
    public = read_json(report)
    if (
        private["independent_human_review"] is not False
        or public["independent_human_review"] is not False
    ):
        raise ValueError("AI/machine review cannot be promoted to independent human review")
    if (
        len(tasks) != len(outputs)
        or len(tasks) != len(private["records"])
        or len(tasks) != len(public["records"])
    ):
        raise ValueError("extraction audit coverage differs")
    if (
        public["verification_sha256"] != sha256_file(verification)
        or public["private_audit_sha256"] != sha256_file(audit)
        or public["extraction_trace_sha256"] != sha256_file(extractions)
        or public["source_trace_sha256"] != sha256_file(trace)
        or private["extraction_trace_sha256"] != sha256_file(extractions)
    ):
        raise ValueError("extraction audit hashes differ")
    for task, output, record, summary in zip(
        tasks, outputs, private["records"], public["records"], strict=True
    ):
        if (
            record["task_sha256"] != task["task_sha256"]
            or output["task_sha256"] != task["task_sha256"]
        ):
            raise ValueError("extraction audit task differs")
        validation = validate_proposal(task, output["raw_proposal"])
        expected = {
            "input_text": task["text"],
            "raw_proposal": output["raw_proposal"],
            "raw_proposal_sha256": digest(output["raw_proposal"]),
            "validated_fields": validation["fields"],
            "kind": task["kind"],
            "interaction_id": task["interaction_id"],
            "evidence_id": task.get("evidence_id"),
            "structural_status": validation["status"],
            "structural_issues": validation["issues"],
            "hit_output_cap_without_eos": output["hit_output_cap_without_eos"],
            "eligible_for_acceptance": False,
        }
        if any(record.get(key) != value for key, value in expected.items()):
            raise ValueError("extraction audit input/output/structural binding differs")
        if summary != {
            k: value
            for k, value in record.items()
            if k not in ("input_text", "raw_proposal", "validated_fields")
        }:
            raise ValueError("public extraction review differs from private source review")
        if not isinstance(record.get("rationale"), str) or not record["rationale"].strip():
            raise ValueError("extraction rationale required")
        if validation["status"] == "span_bound_proposal":
            if (
                record["review_method"] != "AI_assisted_exact_source_review"
                or record["external_truth_verified"] is not False
            ):
                raise ValueError("valid tuple AI review scope differs")
        elif (
            record["review_method"] != "deterministic_contract_validation"
            or record["semantic_review"] != "not_evaluated"
        ):
            raise ValueError("structural failure cannot silently acquire a semantic review")
    expected_counts = {
        "tasks": len(tasks),
        "validation_counts": dict(Counter(r["structural_status"] for r in private["records"])),
        "by_kind": {
            k: dict(Counter(r["structural_status"] for r in private["records"] if r["kind"] == k))
            for k in ("query", "source")
        },
        "semantic_review_counts": dict(Counter(r["semantic_review"] for r in private["records"])),
        "answer_acceptance_enabled": False,
        "actual_new_review_model_calls": 0,
    }
    if any(public.get(k) != value for k, value in expected_counts.items()):
        raise ValueError("extraction audit summary differs from bound records")
    return {
        "records_bound": len(tasks),
        "AI_source_reviewed_proposals": sum(
            r["review_method"] == "AI_assisted_exact_source_review" for r in private["records"]
        ),
        "independent_human_review": False,
        "answer_acceptance_enabled": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-trace", type=Path, required=True)
    p.add_argument("--extractions", type=Path, required=True)
    p.add_argument("--audit", type=Path, required=True)
    p.add_argument("--verification", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(verify(a.source_trace, a.extractions, a.audit, a.verification, a.report)))
