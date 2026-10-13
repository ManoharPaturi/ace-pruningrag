"""Combine valid and rejected AI inventory assessments without hiding pending tasks."""

import json
from collections import Counter

from .claim_extraction import digest
from .claim_inventory import validate


def summarize(tasks, outputs, valid_records, rejected_records):
    if len(tasks) != len(outputs) or not tasks:
        raise ValueError("inventory role review task/output coverage differs")
    indexed = {}
    for index, (task, output) in enumerate(zip(tasks, outputs, strict=True)):
        key = task["task_sha256"]
        if (
            key in indexed
            or digest({k: v for k, v in task.items() if k != "task_sha256"}) != key
            or output["task_sha256"] != key
            or output["kind"] != task["kind"]
            or output["validation"] != validate(task, output["raw_proposal"])
        ):
            raise ValueError("inventory role review task identity or raw validation differs")
        indexed[key] = (index, task, output)
    valid_keys = {
        k
        for k, (_, _, r) in indexed.items()
        if r["validation"]["status"] == "bound_inventory_proposal"
    }
    seen, valid_seen, ledger, references = set(), set(), [], {}
    for records, admitted in ((valid_records, True), (rejected_records, False)):
        for record in records:
            key = record["task_sha256"]
            if key in seen or key not in indexed or (key in valid_keys) != admitted:
                raise ValueError("inventory role review duplicate or mismatched admission")
            seen.add(key)
            index, task, output = indexed[key]
            if (
                record["kind"] != task["kind"]
                or record["interaction_id"] != task["interaction_id"]
                or record.get("evidence_id") != task.get("evidence_id")
                or record["input_text"] != task["text"]
                or record["raw_proposal"] != output["raw_proposal"]
                or record["raw_proposal_sha256"] != digest(output["raw_proposal"])
                or record["reviewer_type"] != "AI"
                or not isinstance(record["rationale"], str)
                or not record["rationale"].strip()
                or record["semantic_status"]
                not in (
                    "partial_or_misbound_requirements",
                    "conditional_example_with_role_errors",
                    "role_or_scope_errors",
                    "table_or_navigation_misbound",
                    "metadata_role_errors",
                    "mixed_claims_with_role_errors",
                    "coherent_partial_claims",
                    "unresolved",
                    "unparseable_capped_output",
                )
                or any(
                    record[k] is not False
                    for k in (
                        "independent_human_review",
                        "full_requirement_coverage_verified",
                        "eligible_for_answer_acceptance",
                        "external_truth_verified",
                    )
                )
            ):
                raise ValueError("inventory role review input/output binding or scope differs")
            try:
                proposal = json.loads(output["raw_proposal"])
            except ValueError:
                proposal = None
            frames = proposal.get("frames", []) if isinstance(proposal, dict) else []
            count = len(frames) if isinstance(frames, list) else 0
            pair = digest([task["kind"], task["text"], output["raw_proposal"]])
            if admitted:
                valid_seen.add(key)
            else:
                if (
                    type(record["index"]) is not int
                    or record["index"] != index
                    or type(record["parsed_frames_assessed"]) is not int
                    or record["parsed_frames_assessed"] != count
                ):
                    raise ValueError("rejected inventory frame assessment coverage differs")
                reuse = record["assessment_reused_from_index"]
                if reuse is not None and (
                    type(reuse) is not int
                    or reuse not in references
                    or references[reuse] != (pair, record["semantic_status"], record["rationale"])
                ):
                    raise ValueError(
                        "inventory role review reuse differs from exact input/proposal"
                    )
                if record["semantic_status"] == "unparseable_capped_output" and (
                    proposal is not None or output["hit_output_cap_without_eos"] is not True
                ):
                    raise ValueError("inventory role review unparseable/cap scope differs")
            references[index] = (pair, record["semantic_status"], record["rationale"])
            ledger.append(
                {
                    "index": index,
                    "task_sha256": key,
                    "kind": task["kind"],
                    "raw_proposal_sha256": digest(output["raw_proposal"]),
                    "input_proposal_pair_sha256": pair,
                    "structural_status": output["validation"]["status"],
                    "parsed_frames_assessed": count,
                    "semantic_status": record["semantic_status"],
                    "rationale": record["rationale"],
                    "assessment_reused_from_index": record.get("assessment_reused_from_index"),
                    "reviewer_type": "AI",
                    "independent_human_review": False,
                }
            )
    if valid_seen != valid_keys:
        raise ValueError("valid inventory role review coverage incomplete")
    return {
        "scope": (
            "AI role/omission review across valid/rejected inventories; pending tasks retained"
        ),
        "total_tasks": len(tasks),
        "AI_assessed_tasks": len(seen),
        "valid_inventories_assessed": len(valid_seen),
        "rejected_inventories_assessed": len(seen - valid_seen),
        "rejected_inventories_pending_assessment": len(indexed) - len(seen),
        "all_inventory_tasks_assessed": seen == set(indexed),
        "assessment_counts_by_kind": dict(Counter(r["kind"] for r in ledger)),
        "distinct_input_proposal_pairs": len({r["input_proposal_pair_sha256"] for r in ledger}),
        "parsed_frames_assessed": sum(r["parsed_frames_assessed"] for r in ledger),
        "AI_semantic_categories": dict(Counter(r["semantic_status"] for r in ledger)),
        "independent_human_review": False,
        "semantic_requirement_accuracy": None,
        "full_requirement_coverage_verified": False,
        "answer_acceptance_enabled": False,
        "records": sorted(ledger, key=lambda r: r["index"]),
    }
