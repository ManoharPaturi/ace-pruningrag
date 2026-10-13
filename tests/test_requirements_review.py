import copy
import json

import pytest

from ace_pruningrag.claim_extraction import digest
from ace_pruningrag.query_requirements import validate
from ace_pruningrag.requirements_review import summarize


def fixture():
    task = {"kind": "query", "interaction_id": "q", "text": "Who won?", "query_time": "2024"}
    task["task_sha256"] = digest(task)
    raw = json.dumps(
        {
            "status": "partial",
            "composition": "all",
            "cardinality": None,
            "variables": [],
            "clauses": [],
            "operation": {"kind": "unknown", "cue": None, "operands": [], "result": None},
        }
    )
    output = {
        "task_sha256": task["task_sha256"],
        "raw_proposal": raw,
        "validation": validate(task, raw),
    }
    checklist = {
        "gold_or_prediction_used": False,
        "source_excerpt_used": False,
        "independent_human_review": False,
        "answer_acceptance_enabled": False,
        "records": [
            {
                "index": 0,
                "task_sha256": task["task_sha256"],
                "interaction_id": "q",
                "query_text": task["text"],
                "query_time": "2024",
                "required_checks": ["Unknown winner"],
                "reviewer_kind": "ai",
                "independent_human_review": False,
                "semantic_extraction_pass": None,
            }
        ],
    }
    batch = {
        "records": [
            {
                "index": 0,
                "task_sha256": task["task_sha256"],
                "interaction_id": "q",
                "input_text": task["text"],
                "raw_proposal": raw,
                "raw_proposal_sha256": digest(raw),
                "reviewer_type": "AI",
                "semantic_status": "unresolved",
                "rationale": "Empty proposal cannot establish winner relation.",
                "independent_human_review": False,
                "full_requirement_coverage_verified": False,
                "eligible_for_answer_acceptance": False,
                "external_truth_verified": False,
            }
        ]
    }
    return [task], [output], checklist, batch


def test_ai_review_scope_remains_unverified_even_for_bound_empty_proposal():
    result = summarize(*fixture())
    assert result["structurally_bound_proposals"] == 1
    assert result["query_proposal_role_review_complete"]
    assert result["AI_semantic_categories"] == {"unresolved": 1}
    assert result["semantic_requirement_accuracy"] is None
    assert not result["full_requirement_coverage_verified"]
    assert not result["independent_human_review"] and not result["answer_acceptance_enabled"]


def test_review_rejects_changed_inputs_raw_outputs_coverage_and_promoted_scope():
    original = fixture()
    for mutate in (
        lambda x: x[0][0].update(text="Who lost?"),
        lambda x: x[1][0].update(raw_proposal="{}"),
        lambda x: x[2]["records"][0].update(query_time="2025"),
        lambda x: x[2].update(gold_or_prediction_used=True),
        lambda x: x[3]["records"][0].update(raw_proposal_sha256="0" * 64),
        lambda x: x[3]["records"][0].update(eligible_for_answer_acceptance=True),
        lambda x: x[3]["records"].append(copy.deepcopy(x[3]["records"][0])),
        lambda x: x[3].update(records=[]),
        lambda x: x[2].update(records=[]),
    ):
        changed = copy.deepcopy(original)
        mutate(changed)
        with pytest.raises(ValueError):
            summarize(*changed)
