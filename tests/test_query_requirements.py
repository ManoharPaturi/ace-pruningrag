import copy
import json

from ace_pruningrag.query_requirements import CLAUSE_FIELDS, character_parser, messages, validate


def variable(identifier, kind, role, cue, constant=None, value_type="entity"):
    return {
        "id": identifier,
        "kind": kind,
        "role": role,
        "value_type": value_type,
        "cue": cue,
        "constant": constant,
    }


def clause(text, **fields):
    return {k: text if k == "text" else fields.get(k) for k in CLAUSE_FIELDS}


def plan(variables, clauses, composition="all", operation=None):
    return {
        "status": "partial",
        "composition": composition,
        "cardinality": None,
        "variables": variables,
        "clauses": clauses,
        "operation": operation or {"kind": "unknown", "cue": None, "operands": [], "result": None},
    }


def task(text):
    return {
        "kind": "query",
        "text": text,
        "query_time": "2024-01-01",
        "gold": "PRIVATE ANSWER",
        "prediction": "PRIVATE PREDICTION",
    }


def accepts(t, p):
    parser = character_parser(t)
    for char in json.dumps(p, ensure_ascii=False, separators=(",", ":")):
        if char not in parser.get_allowed_characters():
            return False
        parser = parser.add_character(char)
    return parser.can_end()


def test_decoder_preserves_known_constraints_and_rejects_guessed_or_undeclared_answers():
    t = task("Who won 14 awards?")
    p = plan(
        [variable("v0", "answer", "subject", "Who")],
        [clause(t["text"], subject={"variable": "v0"}, value={"span": "14"})],
    )
    assert accepts(t, p)
    assert validate(t, json.dumps(p))["status"] == "bound_requirement_proposal"
    for mutate in (
        lambda x: x["variables"][0].update(constant="14"),
        lambda x: x["variables"][0].update(id="v1"),
        lambda x: x["clauses"][0].update(subject={"variable": "v7"}),
        lambda x: x["operation"].update(operands=["v7"]),
        lambda x: x["operation"].update(result="v7"),
        lambda x: x["clauses"][0].update(value={"span": "invented"}),
    ):
        bad = copy.deepcopy(p)
        mutate(bad)
        assert not accepts(t, bad)


def test_decoder_retains_validation_gate_for_local_bindings_roles_and_arity():
    t = task("Who won 14 awards and was born in 1990?")
    p = plan(
        [variable("v0", "answer", "subject", "Who")],
        [clause("won 14 awards", value={"span": "1990"})],
    )
    assert accepts(t, p)  # A global copied span is not proof of clause-local support.
    assert validate(t, json.dumps(p))["issues"] == ["outside_clause_clause_0_value"]
    p["clauses"][0]["value"] = {"variable": "v0"}
    assert accepts(t, p)
    assert "inconsistent_variable_role_clause_0_value" in validate(t, json.dumps(p))["issues"]
    p["operation"] = {"kind": "product", "cue": "won", "operands": [], "result": "v0"}
    assert accepts(t, p)
    assert "operation_arity_inconsistent" in validate(t, json.dumps(p))["issues"]


def test_decoder_unicode_empty_intent_and_limits():
    t = task("Victoria Mone\u0301t won 3 roles")
    p = plan([variable("v0", "answer", "value", "roles")], [clause(t["text"])])
    p["clauses"][0]["subject"] = {"span": "Victoria Mone\u0301t"}
    assert accepts(t, p)
    p["clauses"][0]["subject"] = {"span": "Victoria Mone"}
    assert not accepts(t, p)
    p["clauses"] = [clause(t["text"])] * 13
    assert not accepts(t, p)
    p = plan([], [])
    p["status"] = "ambiguous"
    assert accepts(task(""), p)
    assert validate(task(""), json.dumps(p))["warnings"]


def test_real_token_filter_allows_declared_references_and_only_complete_termination():
    from lmformatenforcer import TokenEnforcer, TokenEnforcerTokenizerData

    t = task('Who won 14 "awards"?')
    p = plan(
        [variable("v0", "answer", "subject", "Who")],
        [clause(t["text"], subject={"variable": "v0"}, value={"span": "14"})],
    )
    output = json.dumps(p, ensure_ascii=False, separators=(",", ":"))
    alphabet = sorted(set(output + t["text"]))
    encode = {char: i for i, char in enumerate(alphabet)}
    decode = {i: char for char, i in encode.items()}
    data = TokenEnforcerTokenizerData(
        [(i, c, False) for c, i in encode.items()],
        lambda ids: "".join(decode.get(i, "") for i in ids),
        999,
        False,
        1000,
    )
    enforcer = TokenEnforcer(data, character_parser(t))
    prefix = [998]
    for char in output:
        allowed = enforcer.get_allowed_tokens(prefix).allowed_tokens
        assert encode[char] in allowed
        assert 999 not in allowed
        prefix.append(encode[char])
    assert 999 in enforcer.get_allowed_tokens(prefix).allowed_tokens


def test_explicit_constraint_is_distinct_from_unknown_answer_and_labels_are_blinded():
    t = task("Who won 14 awards?")
    p = plan(
        [variable("v0", "answer", "subject", "Who")],
        [
            clause(
                t["text"],
                subject={"variable": "v0"},
                relation="won",
                value={"span": "14"},
                unit="awards",
            )
        ],
        operation={"kind": "select", "cue": "Who", "operands": [], "result": "v0"},
    )
    r = validate(t, json.dumps(p))
    assert r["status"] == "bound_requirement_proposal"
    assert r["clauses"][0]["value"]["text"] == "14"
    assert r["variables"]["v0"]["constant"] is None
    assert r["query_time_anchor"] == t["query_time"]
    assert not r["semantic_requirements_verified"]
    assert not r["answer_acceptance_enabled"]
    assert "PRIVATE" not in json.dumps(messages(t))
    bad = copy.deepcopy(p)
    bad["variables"][0]["constant"] = "14"
    assert "variable_0_answer_assignment_forbidden" in validate(t, json.dumps(bad))["issues"]
    bad = copy.deepcopy(p)
    bad["clauses"][0]["subject"] = {"span": "Taylor Swift"}
    assert validate(t, json.dumps(bad))["status"] == "invalid_requirement_proposal"


def test_shared_unknown_entity_retains_multiple_constraints():
    t = task("Who won 14 awards and was born in 1990?")
    p = plan(
        [variable("v0", "answer", "subject", "Who")],
        [
            clause(
                "won 14 awards",
                subject={"variable": "v0"},
                relation="won",
                value={"span": "14"},
                unit="awards",
            ),
            clause(
                "was born in 1990",
                subject={"variable": "v0"},
                relation="born",
                value={"span": "1990"},
            ),
        ],
    )
    r = validate(t, json.dumps(p))
    assert r["status"] == "bound_requirement_proposal"
    assert len(r["clauses"]) == 2
    bad = copy.deepcopy(p)
    bad["clauses"][0]["value"] = {"span": "1990"}
    assert "outside_clause_clause_0_value" in validate(t, json.dumps(bad))["issues"]


def test_comparison_links_context_entities_latent_values_and_unknown_result():
    t = task("Compare A and B heights")
    variables = [
        variable("v0", "answer", "result", "Compare", value_type="comparison"),
        variable("v1", "context", "subject", "A", "A"),
        variable("v2", "context", "subject", "B", "B"),
        variable("v3", "latent", "value", "heights", value_type="number"),
        variable("v4", "latent", "value", "heights", value_type="number"),
    ]
    p = plan(
        variables,
        [
            clause(
                t["text"], subject={"variable": "v1"}, relation="heights", value={"variable": "v3"}
            ),
            clause(
                t["text"], subject={"variable": "v2"}, relation="heights", value={"variable": "v4"}
            ),
        ],
        composition="comparison",
    )
    assert validate(t, json.dumps(p))["status"] == "bound_requirement_proposal"
    bad = copy.deepcopy(p)
    bad["clauses"][0]["value"] = {"variable": "v1"}
    assert "inconsistent_variable_role_clause_0_value" in validate(t, json.dumps(bad))["issues"]
    bad = copy.deepcopy(p)
    bad["clauses"][0]["subject"] = {"variable": "v7"}
    assert "undeclared_variable_clause_0_subject" in validate(t, json.dumps(bad))["issues"]


def test_operations_cannot_supply_results_overwrite_constants_or_cycle():
    t = task("Area of rectangle 17 meters by 66 meters?")
    variables = [
        variable("v0", "answer", "result", "Area", value_type="number"),
        variable("v1", "context", "value", "17", "17", "number"),
        variable("v2", "context", "value", "66", "66", "number"),
    ]
    p = plan(
        variables,
        [
            clause(t["text"], value={"variable": "v1"}, unit="meters"),
            clause(t["text"], value={"variable": "v2"}, unit="meters"),
        ],
        composition="calculation",
        operation={"kind": "product", "cue": "by", "operands": ["v1", "v2"], "result": "v0"},
    )
    r = validate(t, json.dumps(p))
    assert r["status"] == "bound_requirement_proposal"
    assert r["variables"]["v0"]["constant"] is None  # Nothing computed or answered.
    for mutation, issue in [
        ({"result": "v1"}, "operation_cannot_overwrite_context"),
        ({"operands": ["v0", "v2"]}, "operation_self_dependency"),
        ({"operands": ["v1"]}, "operation_arity_inconsistent"),
    ]:
        bad = copy.deepcopy(p)
        bad["operation"].update(mutation)
        assert issue in validate(t, json.dumps(bad))["issues"]


def test_unicode_cardinality_caps_and_incomplete_intent_remain_unverified():
    t = task("Which 3 roles did Victoria Mone\u0301t play?")
    p = plan(
        [variable("v0", "answer", "value", "Which", value_type="set")],
        [
            clause(
                t["text"],
                subject={"span": "Victoria Mone\u0301t"},
                relation="play",
                value={"variable": "v0"},
            )
        ],
    )
    p["cardinality"] = "3"
    assert validate(t, json.dumps(p))["cardinality"]["text"] == "3"
    bad = copy.deepcopy(p)
    bad["clauses"][0]["subject"] = {"span": "Victoria Mone"}
    assert validate(t, json.dumps(bad))["issues"]
    bad = copy.deepcopy(p)
    bad["clauses"] *= 13
    assert validate(t, json.dumps(bad))["status"] == "invalid_schema"
    empty = plan([], [])
    empty["status"] = "ambiguous"
    assert validate(t, json.dumps(empty))["warnings"]
    empty["status"] = "proposed_complete"
    assert validate(t, json.dumps(empty))["status"] == "invalid_requirement_proposal"
