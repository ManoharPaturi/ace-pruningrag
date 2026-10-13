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


def summarize_ai_audits(paths, trace):
    """Aggregate bound AI judgments without converting uncertainty to errors or human labels."""
    paths = list(paths)
    validation = validate_ai_audits(paths, trace)
    rows = [json.loads(line) for line in trace.read_text().splitlines()]
    reviews = [review for path in paths for review in read_json(path)["reviews"]]
    methods = sorted({row["policy"] for row in rows})
    per_method = {}
    for method in methods:
        expected = [row for row in rows if row["policy"] == method]
        assessed = [review for review in reviews if review["policy"] == method]
        counts = Counter(review["semantic_assessment"] for review in assessed)
        per_method[method] = {
            "responses": len(expected),
            "reviewed": len(assessed),
            "pending": len(expected) - len(assessed),
            "ai_verdicts": {
                verdict: counts[verdict]
                for verdict in ("correct", "incorrect", "uncertain", "abstained")
            },
            "ai_grounding_verdicts": dict(
                Counter(review["grounding_assessment"] for review in assessed)
            ),
        }
    grouped = {}
    for row in rows:
        grouped.setdefault(row["interaction_id"], []).append(row)
    return {
        "scope": "AI-assisted development diagnostics; not independent semantic accuracy",
        "validation": validation,
        "audit_files": [{"name": path.name, "sha256": sha256_file(path)} for path in paths],
        "distinct_questions": len(grouped),
        "questions_with_identical_predictions": sum(
            len({row["prediction"] for row in group}) == 1 for group in grouped.values()
        ),
        "per_method": per_method,
        "independent_human_review": False,
        "limitations": [
            "Uncertain, abstained and pending responses retain separate counts.",
            "Repeated methods share questions; response records are not independent cases.",
            "Different grounding categories do not constitute calibrated support scores.",
            "AI verdict counts alone cannot promote a selector or establish cross-source benefit.",
        ],
    }
