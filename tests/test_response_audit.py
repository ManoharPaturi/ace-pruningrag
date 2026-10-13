import copy
import json

import pytest

from ace_pruningrag.artifacts import sha256_file, write_json
from ace_pruningrag.response_audit import summarize_ai_audits, validate_ai_audits


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


def test_false_abstention_label_rejected(tmp_path):
    trace, audit = packet(tmp_path)
    audit["reviews"][0]["semantic_assessment"] = "abstained"
    path = tmp_path / "audit.json"
    write_json(path, audit)
    with pytest.raises(ValueError, match="abstention"):
        validate_ai_audits([path], trace)


def test_prose_abstention_requires_an_exact_actual_response_span(tmp_path):
    trace, audit = packet(tmp_path)
    original = json.loads(trace.read_text())
    original["prediction"] = "No dated evidence is supplied. I don't know."
    trace.write_text(json.dumps(original) + "\n")
    audit["trace_sha256"] = sha256_file(trace)
    review = audit["reviews"][0]
    review["prediction"] = original["prediction"]
    review["semantic_assessment"] = "abstained"
    review["explicit_abstention_span"] = "I don't know."
    path = tmp_path / "audit.json"
    write_json(path, audit)
    assert validate_ai_audits([path], trace)["explicit_prose_abstentions"] == 1
    review["explicit_abstention_span"] = "I do not know."
    write_json(path, audit)
    with pytest.raises(ValueError, match="span"):
        validate_ai_audits([path], trace)


def test_summary_keeps_pending_uncertain_and_repeated_questions_separate(tmp_path):
    trace, audit = packet(tmp_path)
    original = json.loads(trace.read_text())
    other_method = {**original, "policy": "coverage"}
    other_question = {**original, "interaction_id": "other", "prediction": "I don't know."}
    trace.write_text("\n".join(map(json.dumps, [original, other_method, other_question])) + "\n")
    audit["trace_sha256"] = sha256_file(trace)
    abstention = {
        **audit["reviews"][0],
        "interaction_id": "other",
        "prediction": "I don't know.",
        "semantic_assessment": "abstained",
    }
    audit["reviews"].append(abstention)
    path = tmp_path / "audit.json"
    write_json(path, audit)
    result = summarize_ai_audits(iter([path]), trace)
    assert result["distinct_questions"] == 2
    assert result["validation"]["response_count"] == 3
    assert result["per_method"]["coverage"]["pending"] == 1
    assert result["per_method"]["top_k"]["ai_verdicts"] == {
        "correct": 0,
        "incorrect": 0,
        "uncertain": 1,
        "abstained": 1,
    }
    assert not result["validation"]["full_ai_response_audit_complete"]


def test_summary_rejects_tampered_review_before_aggregation(tmp_path):
    trace, audit = packet(tmp_path)
    audit["reviews"][0]["selected_evidence_ids"] = ["invented-source"]
    path = tmp_path / "audit.json"
    write_json(path, audit)
    with pytest.raises(ValueError, match="differs"):
        summarize_ai_audits([path], trace)
