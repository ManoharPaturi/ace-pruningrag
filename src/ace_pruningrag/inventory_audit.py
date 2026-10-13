"""Inventory bookkeeping that never promotes structural checks to semantic review."""

import json
from collections import Counter

from .claim_extraction import digest
from .claim_inventory import FIELDS, validate


def summarize(tasks, records):
    if len(tasks) != len(records):
        raise ValueError("inventory audit task coverage differs")
    seen, ledger = set(), []
    counts = {
        kind: {
            "tasks": 0,
            "parsed_frames": 0,
            "structurally_admitted_frames": 0,
            "validation_counts": Counter(),
            "proposed_inventory_states": Counter(),
            "parsed_frame_count_histogram": Counter(),
            "nonnull_role_counts_in_admitted_frames": Counter(),
            "warning_counts": Counter(),
            "capped_outputs": 0,
        }
        for kind in ("query", "source")
    }
    for task, record in zip(tasks, records, strict=True):
        key = task["task_sha256"]
        if (
            key in seen
            or digest({k: v for k, v in task.items() if k != "task_sha256"}) != key
            or record["task_sha256"] != key
            or record["kind"] != task["kind"]
        ):
            raise ValueError("inventory audit duplicate or changed task identity")
        seen.add(key)
        validation = validate(task, record["raw_proposal"])
        if validation != record["validation"]:
            raise ValueError("inventory audit validation differs from raw proposal")
        kind = counts[task["kind"]]
        kind["tasks"] += 1
        kind["validation_counts"][validation["status"]] += 1
        kind["warning_counts"].update(validation.get("warnings", []))
        # This records the decoder's termination flag, not an independent token proof.
        kind["capped_outputs"] += int(record["hit_output_cap_without_eos"])
        try:
            parsed = json.loads(record["raw_proposal"])
        except ValueError:
            parsed = None
        frames = parsed.get("frames", []) if isinstance(parsed, dict) else []
        if not isinstance(frames, list):
            frames = []
        count = len(frames)
        kind["parsed_frames"] += count
        kind["parsed_frame_count_histogram"][str(count)] += 1
        if isinstance(parsed, dict) and isinstance(parsed.get("inventory_status"), str):
            kind["proposed_inventory_states"][parsed["inventory_status"]] += 1
        admitted = validation["status"] == "bound_inventory_proposal"
        if admitted:
            kind["structurally_admitted_frames"] += count
            for frame in frames:
                kind["nonnull_role_counts_in_admitted_frames"].update(
                    name for name in FIELDS if name != "statement" and frame[name] is not None
                )
        ledger.append(
            {
                "task_sha256": key,
                "kind": task["kind"],
                "input_text_sha256": digest(task["text"]),
                "raw_proposal_sha256": digest(record["raw_proposal"]),
                "structural_status": validation["status"],
                "parsed_frames": count,
                "structurally_admitted_frames": count if admitted else 0,
                "warnings": validation.get("warnings", []),
                "reviewer_type": "deterministic_structural_audit",
                "semantic_review_complete": False,
                "complete_requirement_coverage_verified": False,
                "eligible_for_answer_acceptance": False,
            }
        )
    return {
        "scope": "All-task structural inventory audit; real roles and completeness unassessed",
        "tasks": len(tasks),
        "by_kind": {
            key: {
                name: dict(value) if isinstance(value, Counter) else value
                for name, value in v.items()
            }
            for key, v in counts.items()
        },
        "records": ledger,
        "semantic_review_pending_tasks": len(tasks),
        "independent_human_review": False,
        "semantic_roles_verified": False,
        "full_requirement_coverage_verified": False,
        "answer_acceptance_enabled": False,
    }
