"""Bind AI-assisted response assessments without promoting them to human labels."""

import json
from collections import Counter

from .artifacts import read_json, sha256_file


def validate_ai_audits(paths, trace):
    rows = [json.loads(line) for line in trace.read_text().splitlines()]
    lookup = {(r["interaction_id"], r["policy"]): r for r in rows}
    if len(lookup) != len(rows):
        raise ValueError("duplicate trace identity")
    seen, assessments = set(), []
    digest = sha256_file(trace)
    for path in paths:
        audit = read_json(path)
        if (
            audit.get("artifact_type") != "ai_assisted_response_audit"
            or audit.get("trace_sha256") != digest
            or audit.get("independent_human_review") is not False
            or not isinstance(audit.get("reviewer"), str)
            or not audit["reviewer"].strip()
        ):
            raise ValueError("AI audit type, trace binding and reviewer required")
        for review in audit["reviews"]:
            key = (review["interaction_id"], review["policy"])
            if key not in lookup or key in seen:
                raise ValueError("duplicate or unknown audited response")
            original = lookup[key]
            if (
                review.get("reviewer_type") != "AI"
                or review.get("human_validated") is not False
                or review.get("prediction") != original["prediction"]
                or review.get("prompt_sha256") != original["prompt_sha256"]
                or review.get("selected_evidence_ids")
                != [e["evidence_id"] for e in original["selected"]]
            ):
                raise ValueError(
                    "assessment differs from actual response/evidence or implies human review"
                )
            if review.get("semantic_assessment") not in (
                "correct",
                "incorrect",
                "uncertain",
                "abstained",
            ):
                raise ValueError("unknown AI semantic verdict")
            abstained = original["prediction"].strip().casefold() in (
                "i don't know",
                "i don't know.",
                "i do not know",
                "i do not know.",
            )
            span = review.get("explicit_abstention_span")
            prose_abstention = (
                isinstance(span, str)
                and span.strip().casefold()
                in ("i don't know", "i don't know.", "i do not know", "i do not know.")
                and span in original["prediction"]
            )
            if abstained and review["semantic_assessment"] != "abstained":
                raise ValueError("AI abstention verdict contradicts the actual response")
            if review["semantic_assessment"] == "abstained" and not (abstained or prose_abstention):
                raise ValueError("AI abstention verdict requires an actual bound response span")
            if not all(
                isinstance(review.get(k), str) and review[k].strip()
                for k in ("grounding_assessment", "reason")
            ):
                raise ValueError("grounding verdict and explanatory reason required")
            seen.add(key)
            assessments.append(review)
    return {
        "status": "ai_assessments_structurally_validated",
        "trace_sha256": digest,
        "response_count": len(rows),
        "ai_reviewed_responses": len(seen),
        "ai_reviewed_questions": len({qid for qid, _ in seen}),
        "unreviewed_responses": len(rows) - len(seen),
        "full_ai_response_audit_complete": seen == set(lookup),
        "ai_semantic_verdicts": dict(Counter(r["semantic_assessment"] for r in assessments)),
        "ai_grounding_verdicts": dict(Counter(r["grounding_assessment"] for r in assessments)),
        "explicit_prose_abstentions": sum(
            r["semantic_assessment"] == "abstained" and bool(r.get("explicit_abstention_span"))
            for r in assessments
        ),
        "independent_human_review": False,
        "semantic_truth_verified_by_validator": False,
        "limitations": [
            "Binding identifies the assessed response; it does not prove the AI judgment correct.",
            "AI assessments cannot replace independent human labels or resolve them silently.",
        ],
    }
