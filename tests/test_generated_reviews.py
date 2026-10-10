import json

import pytest

from ace_pruningrag.generated_reviews import import_generated_review, validate_generated_review


def packet(tmp_path, decision="uncertain", support="supported", outcome="needs_semantic_review"):
    prediction = {
        "interaction_id": "q1",
        "policy": "fixed_web",
        "prediction": "answer",
        "prompt_sha256": "prompt-hash",
        "evaluation": {"outcome": outcome},
    }
    trace = tmp_path / "predictions.jsonl"
    trace.write_text(json.dumps(prediction) + "\n")
    review = prediction | {
        "decision": decision,
        "support": support,
        "attested": True,
        "notes": "Ambiguous.",
    }
    export = tmp_path / "export.json"
    export.write_text(
        json.dumps(
            {
                "artifact_type": "human_review_of_generated_answers",
                "reviewer": "Reviewer",
                "reviews": [review],
            }
        )
    )
    return export, trace


def test_uncertain_is_not_scored_incorrect_and_import_is_immutable(tmp_path):
    export, trace = packet(tmp_path)
    result = import_generated_review(export, trace, tmp_path / "imported")
    policy = result["per_policy"]["fixed_web"]
    assert policy["decisions"] == {"uncertain": 1}
    assert policy["correct_fraction_bounds"] == [0, 1]
    assert result["all_correctness_resolved"] is False
    assert (tmp_path / "imported/original-export.json").read_bytes() == export.read_bytes()
    with pytest.raises(FileExistsError):
        import_generated_review(export, trace, tmp_path / "imported")


@pytest.mark.parametrize(
    "field,value",
    [
        ("prediction", "changed"),
        ("prompt_sha256", "changed"),
        ("attested", False),
        ("decision", "invented"),
        ("support", "pending"),
    ],
)
def test_rejects_mismatched_or_unattested_verdict(tmp_path, field, value):
    export, trace = packet(tmp_path)
    data = json.loads(export.read_text())
    data["reviews"][0][field] = value
    export.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        validate_generated_review(export, trace)


def test_rejects_duplicate_and_false_abstention(tmp_path):
    export, trace = packet(tmp_path)
    data = json.loads(export.read_text())
    data["reviews"].append(data["reviews"][0])
    export.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="duplicate"):
        validate_generated_review(export, trace)
    export, trace = packet(tmp_path, "abstained", "not_applicable")
    with pytest.raises(ValueError, match="abstention"):
        validate_generated_review(export, trace)


def test_missing_reviews_remain_unresolved(tmp_path):
    export, trace = packet(tmp_path, "correct")
    extra = json.loads(trace.read_text()) | {"interaction_id": "q2"}
    with trace.open("a") as stream:
        stream.write(json.dumps(extra) + "\n")
    result = validate_generated_review(export, trace)
    assert result["full_prediction_coverage"] is False
    assert result["per_policy"]["fixed_web"]["correct_fraction_bounds"] == [0.5, 1]
