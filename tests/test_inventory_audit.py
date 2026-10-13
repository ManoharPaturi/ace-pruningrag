import json

import pytest

from ace_pruningrag.claim_extraction import digest
from ace_pruningrag.claim_inventory import FIELDS, validate
from ace_pruningrag.inventory_audit import summarize


def task(text, kind="source"):
    value = {"kind": kind, "interaction_id": text, "text": text}
    return {**value, "task_sha256": digest(value)}


def proposal(statement, **fields):
    return json.dumps(
        {
            "inventory_status": "proposed_complete",
            "frames": [{k: statement if k == "statement" else fields.get(k) for k in FIELDS}],
        }
    )


def record(t, raw, capped=False):
    return {
        "task_sha256": t["task_sha256"],
        "kind": t["kind"],
        "raw_proposal": raw,
        "validation": validate(t, raw),
        "hit_output_cap_without_eos": capped,
    }


def test_all_proposed_frames_are_counted_without_semantic_promotion():
    t = task("A won? A won?")
    raw = proposal("A won?", subject="A", relation="won")
    result = summarize([t], [record(t, raw)])
    assert result["by_kind"]["source"]["structurally_admitted_frames"] == 1
    assert result["by_kind"]["source"]["proposed_inventory_states"] == {"proposed_complete": 1}
    assert result["by_kind"]["source"]["warning_counts"]
    assert result["semantic_review_pending_tasks"] == 1
    assert not result["full_requirement_coverage_verified"]
    assert not result["records"][0]["eligible_for_answer_acceptance"]


def test_invalid_query_answers_and_capped_outputs_are_retained_not_admitted():
    a, b = task("A won.", "query"), task("B lost.")
    result = summarize([a, b], [record(a, proposal(a["text"], value="A")), record(b, "{", True)])
    assert result["by_kind"]["query"]["parsed_frames"] == 1
    assert result["by_kind"]["query"]["structurally_admitted_frames"] == 0
    assert result["by_kind"]["source"]["capped_outputs"] == 1
    assert result["semantic_review_pending_tasks"] == 2
    empty = task("No claims.")
    raw = '{"inventory_status":"partial","frames":[]}'
    assert summarize([empty], [record(empty, raw)])["semantic_review_pending_tasks"] == 1


def test_task_coverage_duplicates_and_forged_validation_are_rejected():
    t = task("A won.")
    r = record(t, proposal(t["text"], subject="A", relation="won"))
    with pytest.raises(ValueError, match="coverage"):
        summarize([t], [])
    with pytest.raises(ValueError, match="duplicate"):
        summarize([t, t], [r, r])
    with pytest.raises(ValueError, match="identity"):
        summarize([{**t, "text": "B won."}], [r])
    with pytest.raises(ValueError, match="validation"):
        summarize([t], [{**r, "validation": {"status": "supported"}}])
