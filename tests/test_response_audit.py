import copy
import json

import pytest

from ace_pruningrag.artifacts import sha256_file, write_json
from ace_pruningrag.response_audit import validate_ai_audits


def packet(tmp_path):
    trace = tmp_path / "trace.jsonl"
    original = {
        "interaction_id": "q",
        "policy": "top_k",
        "prediction": "answer",
        "prompt_sha256": "prompt",
        "selected": [{"evidence_id": "source"}],
    }
    trace.write_text(json.dumps(original) + "\n")
    review = {
        "interaction_id": "q",
        "policy": "top_k",
        "prediction": "answer",
        "prompt_sha256": "prompt",
        "selected_evidence_ids": ["source"],
        "reviewer_type": "AI",
        "human_validated": False,
        "semantic_assessment": "uncertain",
        "grounding_assessment": "uncertain",
        "reason": "The source does not resolve the requested date.",
    }
    audit = {
        "artifact_type": "ai_assisted_response_audit",
        "reviewer": "AI fixture",
        "trace_sha256": sha256_file(trace),
        "independent_human_review": False,
        "reviews": [review],
    }
    return trace, audit


def test_ai_binding_does_not_establish_human_or_semantic_truth(tmp_path):
    trace, audit = packet(tmp_path)
    path = tmp_path / "audit.json"
    write_json(path, audit)
    result = validate_ai_audits([path], trace)
    assert result["full_ai_response_audit_complete"]
    assert not result["independent_human_review"]
    assert not result["semantic_truth_verified_by_validator"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("human_validated", True),
        ("prediction", "changed"),
        ("prompt_sha256", "changed"),
        ("selected_evidence_ids", ["other"]),
    ],
)
def test_binding_rejects_changed_inputs_and_human_promotion(tmp_path, field, value):
    trace, audit = packet(tmp_path)
    audit["reviews"][0][field] = value
    path = tmp_path / "audit.json"
    write_json(path, audit)
    with pytest.raises(ValueError):
        validate_ai_audits([path], trace)


def test_duplicate_batch_assessments_rejected(tmp_path):
    trace, audit = packet(tmp_path)
    audit["reviews"].append(copy.deepcopy(audit["reviews"][0]))
    path = tmp_path / "audit.json"
    write_json(path, audit)
    with pytest.raises(ValueError):
        validate_ai_audits([path], trace)
