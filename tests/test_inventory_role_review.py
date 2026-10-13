import copy
import json

import pytest

from ace_pruningrag.claim_extraction import digest
from ace_pruningrag.claim_inventory import FIELDS, validate
from ace_pruningrag.inventory_role_review import summarize


def fixture():
    tasks, outputs, reviews = [], [], []
    frame = {k: None for k in FIELDS}
    frame.update(statement="A", subject="A", relation="won", value="1")
    raw = json.dumps({"inventory_status": "partial", "frames": [frame]})
    for index in range(2):
        task = {
            "kind": "source",
            "interaction_id": "q",
            "evidence_id": str(index),
            "text": "A won 1.",
        }
        task["task_sha256"] = digest(task)
        tasks.append(task)
        outputs.append(
            {
                "kind": "source",
                "task_sha256": task["task_sha256"],
                "raw_proposal": raw,
                "validation": validate(task, raw),
                "hit_output_cap_without_eos": False,
            }
        )
        reviews.append(
            {
                "index": index,
                "task_sha256": task["task_sha256"],
                "kind": "source",
                "interaction_id": "q",
                "evidence_id": str(index),
                "input_text": task["text"],
                "raw_proposal": raw,
                "raw_proposal_sha256": digest(raw),
                "parsed_frames_assessed": 1,
                "assessment_reused_from_index": None if index == 0 else 0,
                "reviewer_type": "AI",
                "semantic_status": "role_or_scope_errors",
                "rationale": "Relation/value lie outside statement.",
                "independent_human_review": False,
                "full_requirement_coverage_verified": False,
                "eligible_for_answer_acceptance": False,
                "external_truth_verified": False,
            }
        )
    return tasks, outputs, [], reviews


def test_rejected_review_reuse_and_pending_tasks_stay_distinct_from_acceptance():
    result = summarize(*fixture())
    assert result["AI_assessed_tasks"] == 2 and result["distinct_input_proposal_pairs"] == 1
    assert result["parsed_frames_assessed"] == 2 and result["all_inventory_tasks_assessed"]
    assert not result["answer_acceptance_enabled"] and not result["independent_human_review"]
    tasks, outputs, valid, rejected = fixture()
    result = summarize(tasks, outputs, valid, rejected[:1])
    assert result["rejected_inventories_pending_assessment"] == 1
    assert not result["all_inventory_tasks_assessed"]


def test_rejected_review_guards_raw_binding_frame_coverage_and_exact_reuse():
    for mutate in (
        lambda x: x[3][0].update(input_text="B won 1."),
        lambda x: x[3][0].update(raw_proposal_sha256="0" * 64),
        lambda x: x[3][0].update(parsed_frames_assessed=2),
        lambda x: x[3][0].update(parsed_frames_assessed=True),
        lambda x: x[3][1].update(assessment_reused_from_index=1),
        lambda x: x[3][1].update(rationale="Different assessment"),
        lambda x: x[3][0].update(independent_human_review=True),
        lambda x: x[3][0].update(semantic_status="unparseable_capped_output"),
        lambda x: x[3].append(copy.deepcopy(x[3][0])),
    ):
        changed = copy.deepcopy(fixture())
        mutate(changed)
        with pytest.raises(ValueError):
            summarize(*changed)
