"""Bind AI query-proposal review to exact inputs without promoting it to human labels."""

from collections import Counter

from .claim_extraction import digest
from .query_requirements import validate


def summarize(tasks, outputs, checklist, batch):
    if not tasks or len(tasks) != len(outputs):
        raise ValueError("requirements review task/output coverage differs")
    indexed = {}
    for index, (task, output) in enumerate(zip(tasks, outputs, strict=True)):
        key = task["task_sha256"]
        if (
            key in indexed
            or task["kind"] != "query"
            or digest({k: v for k, v in task.items() if k != "task_sha256"}) != key
            or output["task_sha256"] != key
            or output["validation"] != validate(task, output["raw_proposal"])
        ):
            raise ValueError("requirements review task identity or validation differs")
        indexed[key] = (index, task, output)
    if (
        checklist["gold_or_prediction_used"] is not False
        or checklist["source_excerpt_used"] is not False
        or checklist["independent_human_review"] is not False
        or checklist["answer_acceptance_enabled"] is not False
    ):
        raise ValueError("requirements checklist blinding or review scope differs")
    seen = set()
    for item in checklist["records"]:
        key = item["task_sha256"]
        if key in seen or key not in indexed:
            raise ValueError("requirements checklist identity/coverage differs")
        seen.add(key)
        index, task, _ = indexed[key]
        if (
            item["index"] != index
            or item["query_text"] != task["text"]
            or item["query_time"] != task["query_time"]
            or item["interaction_id"] != task["interaction_id"]
            or not item["required_checks"]
            or any(not isinstance(c, str) or not c.strip() for c in item["required_checks"])
            or item["reviewer_kind"] != "ai"
            or item["independent_human_review"] is not False
            or item["semantic_extraction_pass"] is not None
        ):
            raise ValueError("requirements checklist binding differs")
    if seen != set(indexed):
        raise ValueError("requirements checklist coverage incomplete")
    seen, ledger = set(), []
    for record in batch["records"]:
        key = record["task_sha256"]
        if key in seen or key not in indexed:
            raise ValueError("requirements AI review duplicate or unknown identity")
        seen.add(key)
        index, task, output = indexed[key]
        if (
            record["index"] != index
            or record["interaction_id"] != task["interaction_id"]
            or record["input_text"] != task["text"]
            or record["raw_proposal"] != output["raw_proposal"]
            or record["raw_proposal_sha256"] != digest(output["raw_proposal"])
            or record["reviewer_type"] != "AI"
            or record["semantic_status"]
            not in (
                "misbound_or_incomplete_requirements",
                "coherent_partial_requirements",
                "unresolved",
            )
            or not isinstance(record["rationale"], str)
            or not record["rationale"].strip()
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
            raise ValueError("requirements AI review binding or scope differs")
        ledger.append(
            {
                "index": index,
                "task_sha256": key,
                "raw_proposal_sha256": digest(output["raw_proposal"]),
                "structural_status": output["validation"]["status"],
                "semantic_status": record["semantic_status"],
                "rationale": record["rationale"],
                "reviewer_type": "AI",
                "independent_human_review": False,
            }
        )
    if seen != set(indexed):
        raise ValueError("requirements AI review coverage incomplete")
    return {
        "scope": "All decoded query proposals AI role/omission reviewed; not independent accuracy",
        "tasks": len(tasks),
        "AI_reviewed_proposals": len(seen),
        "query_proposal_role_review_complete": True,
        "structurally_bound_proposals": sum(
            r["validation"]["status"] == "bound_requirement_proposal" for r in outputs
        ),
        "structural_status_counts": dict(Counter(r["validation"]["status"] for r in outputs)),
        "AI_semantic_categories": dict(Counter(r["semantic_status"] for r in batch["records"])),
        "semantic_requirement_accuracy": None,
        "full_requirement_coverage_verified": False,
        "independent_human_review": False,
        "answer_acceptance_enabled": False,
        "records": sorted(ledger, key=lambda r: r["index"]),
    }
