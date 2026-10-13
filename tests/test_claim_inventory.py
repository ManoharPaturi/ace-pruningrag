import json

from ace_pruningrag.claim_inventory import FIELDS, MAX_FRAMES, messages, validate


def frame(statement, **values):
    return {k: (statement if k == "statement" else values.get(k)) for k in FIELDS}


def raw(*frames, state="partial"):
    return json.dumps({"inventory_status": state, "frames": list(frames)}, ensure_ascii=False)


def test_distinct_events_keep_dates_and_directed_roles_with_exact_spans():
    text = "A bought B in 2001. C bought D in 2017."
    result = validate(
        {"kind": "source", "text": text},
        raw(
            frame(
                "A bought B in 2001.", subject="A", relation="bought", object="B", event_time="2001"
            ),
            frame(
                "C bought D in 2017.", subject="C", relation="bought", object="D", event_time="2017"
            ),
        ),
    )
    assert result["status"] == "bound_inventory_proposal"
    assert result["frames"][1]["object"]["spans"] == [[29, 30]]
    assert not result["semantic_roles_verified"]
    mixed = frame("A bought B in 2001.", subject="A", relation="bought", event_time="2017")
    assert validate({"kind": "source", "text": text}, raw(mixed))["issues"]


def test_comparison_requirements_have_multiple_operands_but_no_answer():
    task = {"kind": "query", "text": "Compare A and B sales in 2020."}
    result = validate(
        task,
        raw(
            frame(task["text"], subject="A", relation="sales", event_time="2020"),
            frame(task["text"], subject="B", relation="sales", event_time="2020"),
            state="proposed_complete",
        ),
    )
    assert len(result["frames"]) == 2
    assert not result["complete_requirement_coverage_verified"]
    bad = frame(task["text"], subject="A", relation="sales", value="2020")
    assert "frame_0_query_answer_proposed" in validate(task, raw(bad))["issues"]
    contaminated = {**task, "gold": "PRIVATE LABEL", "prediction": "PRIVATE ANSWER"}
    assert "PRIVATE" not in json.dumps(messages(contaminated))


def test_negation_bounds_attribution_and_observation_date_are_distinct():
    text = "As of 2024, X reportedly did not win more than 2 awards in 2023."
    f = frame(
        text,
        subject="X",
        relation="win",
        value="2",
        unit="awards",
        event_time="2023",
        observation_time="2024",
        qualification="did not win more than",
        attribution="reportedly",
    )
    result = validate({"kind": "source", "text": text}, raw(f))
    assert result["status"] == "bound_inventory_proposal"
    assert result["frames"][0]["event_time"] != result["frames"][0]["observation_time"]
    assert not result["source_truth_verified"] and not result["answer_accepted"]


def test_duplicate_cap_hallucination_and_truncated_unicode_are_rejected():
    text = "Victoria Mone\u0301t won."
    task = {"kind": "source", "text": text}
    f = frame(text, subject="Victoria Mone\u0301t", relation="won")
    assert validate(task, raw(f))["status"] == "bound_inventory_proposal"
    assert validate(task, raw(f, f))["issues"] == ["frame_1_duplicate"]
    assert validate(task, raw(*([f] * (MAX_FRAMES + 1))))["status"] == "invalid_schema"
    for value in ("Victoria Mone", "Someone else", 2):
        bad = {**f, "subject": value}
        assert validate(task, raw(bad))["status"] == "invalid_inventory_proposal"


def test_repeated_occurrences_and_questions_remain_unverified():
    statement = "A won?"
    result = validate(
        {"kind": "source", "text": "A won? A won?"},
        raw(frame(statement, subject="A", relation="won")),
    )
    assert result["frames"][0]["subject"]["spans"] == [[0, 1], [7, 8]]
    assert "frame_0_question_not_verified_assertion" in result["warnings"]
    assert not result["answer_accepted"]


def test_global_span_does_not_allow_a_within_word_local_role_occurrence():
    task = {"kind": "source", "text": "A won. CAT won."}
    result = validate(task, raw(frame("CAT won.", subject="A", relation="won")))
    assert "frame_0_unbound_or_outside_statement_subject" in result["issues"]
    task = {"kind": "source", "text": "A CAT A won."}
    result = validate(task, raw(frame(task["text"], subject="A", relation="won")))
    assert result["frames"][0]["subject"]["spans"] == [[0, 1], [6, 7]]
