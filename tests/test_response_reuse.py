import json

import pytest

from ace_pruningrag.artifacts import sha256_file, write_json
from ace_pruningrag.response_audit import verify_assessment_reuse


def traces(tmp_path):
    row = {
        "interaction_id": "q",
        "policy": "fixed_web",
        "query": "Which item?",
        "query_time": "2024-01-01",
        "prediction": "Item",
        "prompt_sha256": "prompt",
        "selected": [{"evidence_id": "id", "content": "Item is the answer."}],
        "input_tokens": 10,
        "output_tokens": 1,
        "output_ids": [1],
        "generation_seconds": 1,
    }
    source = tmp_path / "source.jsonl"
    source.write_text(json.dumps(row) + "\n")
    target = tmp_path / "target.jsonl"
    target.write_text(json.dumps({**row, "generation_seconds": 2}) + "\n")
    audit = tmp_path / "audit.json"
    write_json(
        audit,
        {
            "artifact_type": "ai_assisted_response_audit",
            "trace_sha256": sha256_file(source),
            "reviewer": "AI fixture",
            "independent_human_review": False,
            "reviews": [
                {
                    "interaction_id": "q",
                    "policy": "fixed_web",
                    "prediction": "Item",
                    "prompt_sha256": "prompt",
                    "selected_evidence_ids": ["id"],
                    "semantic_assessment": "uncertain",
                    "grounding_assessment": "unresolved",
                    "reason": "Fixture only.",
                    "reviewer_type": "AI",
                    "human_validated": False,
                }
            ],
        },
    )
    return source, audit, target


def test_reuse_requires_full_inputs_and_does_not_claim_new_observations(tmp_path):
    source, audit, target = traces(tmp_path)
    result = verify_assessment_reuse(source, [audit], target)
    assert result["response_count"] == 1
    assert result["independent_new_observations"] == 0
    assert result["source_trace_sha256"] != result["target_trace_sha256"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("query_time", "2025-01-01"),
        ("output_ids", [2]),
        ("input_tokens", 11),
        ("selected", [{"evidence_id": "id", "content": "Changed evidence with the same ID."}]),
    ],
)
def test_same_answer_and_ids_cannot_hide_changed_reuse_inputs(tmp_path, field, value):
    source, audit, target = traces(tmp_path)
    row = json.loads(target.read_text())
    row[field] = value
    target.write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="inputs differ"):
        verify_assessment_reuse(source, [audit], target)


def test_missing_field_and_incomplete_source_review_cannot_be_reused(tmp_path):
    source, audit, target = traces(tmp_path)
    row = json.loads(target.read_text())
    del row["output_ids"]
    target.write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="inputs differ"):
        verify_assessment_reuse(source, [audit], target)
    packet = json.loads(audit.read_text())
    packet["reviews"] = []
    write_json(audit, packet)
    with pytest.raises(ValueError, match="complete before reuse"):
        verify_assessment_reuse(source, [audit], target)
