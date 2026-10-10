"""Import human verdicts bound to immutable generated predictions and prompts."""

import json
from collections import Counter
from pathlib import Path

from .artifacts import read_json, sha256_file, write_json


def validate_generated_review(export_path: Path, predictions_path: Path) -> dict:
    export = read_json(export_path)
    if export.get("artifact_type") != "human_review_of_generated_answers":
        raise ValueError("unexpected generated review artifact type")
    if not isinstance(export.get("reviewer"), str) or not export["reviewer"].strip():
        raise ValueError("reviewer identity required")
    predictions = [json.loads(line) for line in predictions_path.read_text().splitlines()]
    lookup = {(row["interaction_id"], row["policy"]): row for row in predictions}
    if not predictions or len(lookup) != len(predictions):
        raise ValueError("prediction identities must be nonempty and unique")
    rows = export.get("reviews")
    if not isinstance(rows, list) or not rows:
        raise ValueError("nonempty reviews required")
    seen = set()
    decisions = {"pending", "correct", "incorrect", "abstained", "uncertain"}
    supports = {"pending", "supported", "unsupported", "uncertain", "not_applicable"}
    for row in rows:
        key = (row["interaction_id"], row["policy"])
        if key in seen or key not in lookup:
            raise ValueError("duplicate or unknown reviewed prediction")
        seen.add(key)
        original = lookup[key]
        if any(row.get(field) != original[field] for field in ("prediction", "prompt_sha256")):
            raise ValueError("review differs from generated answer or prompt")
        decision, support = row.get("decision"), row.get("support")
        if decision not in decisions or support not in supports:
            raise ValueError("unknown correctness or support verdict")
        if not isinstance(row.get("notes"), str) or type(row.get("attested")) is not bool:
            raise ValueError("text notes and explicit attestation required")
        if decision != "pending" and (not row["attested"] or support == "pending"):
            raise ValueError("decided review requires attestation and support verdict")
        is_abstention = original["evaluation"]["outcome"] == "abstained"
        if decision != "pending" and (decision == "abstained") != is_abstention:
            raise ValueError("abstention verdict contradicts generated answer")
        if decision == "abstained" and support != "not_applicable":
            raise ValueError("abstention support must be not applicable")
        if decision not in ("pending", "abstained") and support == "not_applicable":
            raise ValueError("answered prediction requires a support verdict")
    per_policy = {}
    for policy in sorted({row["policy"] for row in predictions}):
        reviewed = [row for row in rows if row["policy"] == policy]
        count = sum(row["policy"] == policy for row in predictions)
        counts = dict(Counter(row["decision"] for row in reviewed))
        unresolved = count - len(reviewed) + counts.get("pending", 0) + counts.get("uncertain", 0)
        correct = counts.get("correct", 0)
        per_policy[policy] = {
            "predictions": count,
            "review_records": len(reviewed),
            "decisions": counts,
            "support": dict(Counter(row["support"] for row in reviewed)),
            "confirmed_correct_fraction": correct / count,
            "correct_fraction_bounds": [correct / count, (correct + unresolved) / count],
            "unresolved_correctness": unresolved,
        }
    return {
        "status": "generated_review_export_validated",
        "export_sha256": sha256_file(export_path),
        "predictions_sha256": sha256_file(predictions_path),
        "review_records": len(rows),
        "distinct_questions": len({row["interaction_id"] for row in rows}),
        "full_prediction_coverage": seen == set(lookup),
        "all_correctness_resolved": seen == set(lookup)
        and all(row["decision"] not in ("pending", "uncertain") for row in rows),
        "per_policy": per_policy,
        "uncertain_query_ids": sorted(
            {row["interaction_id"] for row in rows if row["decision"] == "uncertain"}
        ),
        "scientific_phase3_complete": False,
        "scope": "Human-reviewed development pilot; policy variants are not independent questions.",
    }


def import_generated_review(export_path: Path, predictions_path: Path, output: Path) -> dict:
    result = validate_generated_review(export_path, predictions_path)
    output.mkdir(parents=True, exist_ok=False)
    original = output / "original-export.json"
    original.write_bytes(export_path.read_bytes())
    if sha256_file(original) != result["export_sha256"]:
        raise ValueError("export changed during import")
    write_json(output / "validation.json", result)
    return result
