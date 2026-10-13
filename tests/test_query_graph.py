import copy
import json

import pytest

from ace_pruningrag.query_graph import CLAUSE_FIELDS, validate
from ace_pruningrag.query_graph_decoder import character_parser
from ace_pruningrag.query_graph_prompt import _examples, messages


def var(i, kind, value_type, cue, constant=None, unit=None):
    return {
        "id": f"v{i}",
        "kind": kind,
        "value_type": value_type,
        "cue": cue,
        "constant": constant,
        "unit": unit,
    }


def clause(text, **values):
    return {
        k: text if k == "text" else values.get(k, "positive" if k == "polarity" else None)
        for k in CLAUSE_FIELDS
    }


def plan(variables, clauses=(), operations=(), composition="all"):
    return {
        "status": "partial",
        "composition": composition,
        "cardinality": None,
        "variables": variables,
        "clauses": list(clauses),
        "operations": list(operations),
    }


def operation(kind, cue, result, operands=(), candidates=()):
    return {
        "kind": kind,
        "cue": cue,
        "result": result,
        "operands": list(operands),
        "candidates": list(candidates),
    }


def task(text, time="2024"):
    return {"kind": "query", "text": text, "query_time": time, "gold": "PRIVATE LABEL"}


def accepts(t, p):
    parser = character_parser(t)
    for char in json.dumps(p, ensure_ascii=False, separators=(",", ":")):
        if char not in parser.get_allowed_characters():
            return False
        parser = parser.add_character(char)
    return parser.can_end()


def chain():
    t = task("Who owns the company that publishes Journal B?")
    p = plan(
        [
            var(0, "answer", "entity", "Who"),
            var(1, "latent", "entity", "company"),
            var(2, "context", "entity", "Journal B", "Journal B"),
        ],
        [
            clause(
                "company that publishes Journal B",
                subject={"variable": "v1"},
                relation="publishes",
                object={"variable": "v2"},
            ),
            clause(
                "Who owns the company",
                subject={"variable": "v0"},
                relation="owns",
                object={"variable": "v1"},
            ),
        ],
    )
    return t, p


def test_entity_can_occupy_two_argument_positions_without_erasing_type():
    t, p = chain()
    assert accepts(t, p)
    result = validate(t, json.dumps(p))
    assert result["status"] == "linked_requirement_graph", result
    assert result["variables"]["v1"]["value_type"] == "entity"
    assert not result["semantic_requirements_verified"] and not result["answer_acceptance_enabled"]
    bad = copy.deepcopy(p)
    bad["variables"][1]["value_type"] = "number"
    assert not accepts(t, bad)
    assert "inconsistent_type_clause_0_subject" in validate(t, json.dumps(bad))["issues"]


def test_known_operation_requires_cue_result_arity_and_noncontext_output():
    t = task("Multiply 4 by 5")
    p = plan(
        [
            var(0, "answer", "number", "Multiply"),
            var(1, "context", "number", "4", "4"),
            var(2, "context", "number", "5", "5"),
        ],
        operations=[operation("product", "by", "v0", ["v1", "v2"])],
        composition="calculation",
    )
    assert accepts(t, p)
    assert validate(t, json.dumps(p))["status"] == "linked_requirement_graph"
    for change in (
        {"cue": None},
        {"result": None},
        {"result": "v1"},
        {"operands": ["v1"]},
        {"operands": ["v0", "v2"]},
        {"operands": ["v9", "v2"]},
    ):
        bad = copy.deepcopy(p)
        bad["operations"][0].update(change)
        assert not accepts(t, bad)
        assert validate(t, json.dumps(bad))["issues"]


def test_empty_clauses_and_disconnected_variables_stay_unresolved():
    t, p = chain()
    p["clauses"] = [clause(t["text"])]
    assert accepts(t, p)
    result = validate(t, json.dumps(p))
    assert result["status"] == "unresolved_requirement_graph"
    assert "no_meaningful_requirement_links" in result["warnings"]
    empty = plan([])
    empty["status"] = "ambiguous"
    assert accepts(task(""), empty)
    assert validate(task(""), json.dumps(empty))["status"] == "unresolved_requirement_graph"


def test_predicate_locality_unicode_negation_and_known_quantity_are_retained():
    t = task("Who won 5 awards and never won 2 cups with Victoria Mone\u0301t?")
    p = plan(
        [var(0, "answer", "entity", "Who")],
        [
            clause(
                "won 5 awards",
                subject={"variable": "v0"},
                relation="won",
                value={"span": "5", "value_type": "number"},
                unit="awards",
            ),
            clause(
                "never won 2 cups with Victoria Mone\u0301t",
                subject={"variable": "v0"},
                relation="won",
                polarity="negative",
                object={"span": "Victoria Mone\u0301t", "value_type": "entity"},
                value={"span": "2", "value_type": "number"},
                unit="cups",
                qualification="never",
            ),
        ],
    )
    assert accepts(t, p)
    assert validate(t, json.dumps(p))["status"] == "linked_requirement_graph"
    bad = copy.deepcopy(p)
    bad["clauses"][0]["value"]["span"] = "2"
    assert not accepts(t, bad)
    assert "outside_clause_clause_0_value" in validate(t, json.dumps(bad))["issues"]
    bad = copy.deepcopy(p)
    bad["clauses"][1]["object"]["span"] = "Victoria Mone"
    assert not accepts(t, bad)


def test_multiple_operations_and_input_anchor_keep_unknown_results():
    t = task("How old is A?", "2024-01-01")
    p = plan(
        [
            var(0, "answer", "number", "old"),
            var(1, "anchor", "date", "old"),
            var(2, "latent", "date", "old"),
            var(3, "context", "entity", "A", "A"),
        ],
        [clause(t["text"], subject={"variable": "v3"}, relation="old", period={"variable": "v2"})],
        [operation("age_years", "old", "v0", ["v1", "v2"])],
        "calculation",
    )
    assert accepts(t, p)
    result = validate(t, json.dumps(p))
    assert result["status"] == "linked_requirement_graph"
    assert result["query_time_anchor"] == "2024-01-01"
    assert result["variables"]["v0"]["constant"] is None
    assert not accepts({**t, "query_time": None}, p)
    assert validate({**t, "query_time": None}, json.dumps(p))["issues"]
    t = task("Add 2 and 3 then divide by 5")
    p = plan(
        [
            var(0, "answer", "number", "divide"),
            var(1, "context", "number", "2", "2"),
            var(2, "context", "number", "3", "3"),
            var(3, "context", "number", "5", "5"),
            var(4, "latent", "number", "Add"),
        ],
        operations=[
            operation("sum", "Add", "v4", ["v1", "v2"]),
            operation("quotient", "divide", "v0", ["v4", "v3"]),
        ],
        composition="calculation",
    )
    assert accepts(t, p)
    assert validate(t, json.dumps(p))["status"] == "linked_requirement_graph"
    bad = copy.deepcopy(p)
    bad["operations"][1]["result"] = "v4"
    assert not accepts(t, bad)
    assert "operation_1_duplicate_producer" in validate(t, json.dumps(bad))["issues"]


def test_rank_pairs_measurements_with_candidates_and_rejects_dangling_state():
    t = task("Compare A and B scores")
    p = plan(
        [
            var(0, "answer", "entity", "Compare"),
            var(1, "context", "entity", "A", "A"),
            var(2, "context", "entity", "B", "B"),
            var(3, "latent", "number", "scores"),
            var(4, "latent", "number", "scores"),
        ],
        [
            clause(
                t["text"], subject={"variable": "v1"}, relation="scores", value={"variable": "v3"}
            ),
            clause(
                t["text"], subject={"variable": "v2"}, relation="scores", value={"variable": "v4"}
            ),
        ],
        [operation("argmax", "Compare", "v0", ["v3", "v4"], ["v1", "v2"])],
        "comparison",
    )
    assert accepts(t, p)
    assert validate(t, json.dumps(p))["status"] == "linked_requirement_graph"
    bad = copy.deepcopy(p)
    bad["operations"][0]["candidates"] = ["v1"]
    assert not accepts(t, bad)
    assert "operation_0_candidate_arity" in validate(t, json.dumps(bad))["issues"]
    bad = copy.deepcopy(p)
    bad["variables"].append(var(5, "latent", "entity", "Compare"))
    assert validate(t, json.dumps(bad))["status"] == "unresolved_requirement_graph"
    for proposal in ({}, [], None):
        assert validate(t, json.dumps(proposal))["status"] == "invalid_schema"
    with pytest.raises(ValueError):
        validate({"kind": "source", "text": "A"}, json.dumps(p))


def test_prompt_examples_follow_the_actual_contract_and_exclude_labels():
    for text, proposal in _examples():
        t = task(text)
        assert accepts(t, proposal)
        assert validate(t, json.dumps(proposal))["status"] == "linked_requirement_graph"
    t = {
        **task("Who owns A?"),
        "prediction": "PRIVATE PREDICTION",
        "selected": [{"content": "PRIVATE SOURCE"}],
    }
    assert "PRIVATE" not in json.dumps(messages(t))
    assert "ALL known operations REQUIRE" in messages(t)[0]["content"]


def test_token_filter_and_parser_immutability_for_quoted_unicode_entity():
    from lmformatenforcer import TokenEnforcer, TokenEnforcerTokenizerData

    t = task('Who owns Café "B"?')
    p = plan(
        [var(0, "answer", "entity", "Who"), var(1, "context", "entity", 'Café "B"', 'Café "B"')],
        [clause(t["text"], subject={"variable": "v0"}, relation="owns", object={"variable": "v1"})],
    )
    raw = json.dumps(p, ensure_ascii=False, separators=(",", ":"))
    parser = character_parser(t)
    old_key, old_chars = parser.cache_key(), parser.get_allowed_characters()
    child = parser.add_character("{")
    assert parser.cache_key() == old_key and parser.get_allowed_characters() == old_chars
    assert child.cache_key() != old_key
    assert character_parser(task("Other input")).cache_key() != old_key
    alphabet = sorted(set(raw + t["text"]))
    encode = {char: i for i, char in enumerate(alphabet)}
    decode = {i: char for char, i in encode.items()}
    data = TokenEnforcerTokenizerData(
        [(i, c, False) for c, i in encode.items()],
        lambda ids: "".join(decode.get(i, "") for i in ids),
        999,
        False,
        1000,
    )
    enforcer, prefix = TokenEnforcer(data, parser), [998]
    for char in raw:
        allowed = enforcer.get_allowed_tokens(prefix).allowed_tokens
        assert encode[char] in allowed and 999 not in allowed
        prefix.append(encode[char])
    assert 999 in enforcer.get_allowed_tokens(prefix).allowed_tokens


def test_cycles_assignments_bad_types_and_limits_are_rejected():
    t = task("Add 2 and 3")
    p = plan(
        [
            var(0, "answer", "number", "Add"),
            var(1, "context", "number", "2", "2"),
            var(2, "context", "number", "3", "3"),
            var(3, "latent", "number", "Add"),
            var(4, "latent", "number", "Add"),
        ],
        operations=[
            operation("sum", "Add", "v3", ["v4", "v1"]),
            operation("sum", "Add", "v4", ["v3", "v2"]),
            operation("sum", "Add", "v0", ["v3", "v4"]),
        ],
        composition="calculation",
    )
    assert not accepts(t, p)
    assert "operation_dependency_cycle" in validate(t, json.dumps(p))["issues"]
    t, p = chain()
    bad = copy.deepcopy(p)
    bad["variables"][0]["constant"] = "Journal B"
    assert not accepts(t, bad)
    assert "variable_0_unknown_assignment_forbidden" in validate(t, json.dumps(bad))["issues"]
    for key, oversized in (
        ("variables", [p["variables"][0]] * 9),
        ("clauses", [p["clauses"][0]] * 13),
        ("operations", [operation("unknown", None, None)] * 9),
    ):
        bad = copy.deepcopy(p)
        bad[key] = oversized
        assert not accepts(t, bad)
        assert validate(t, json.dumps(bad))["status"] == "invalid_schema"


def test_answer_cannot_feed_a_latent_operation_even_without_a_cycle():
    t = task("Add 2 and 3")
    p = plan(
        [
            var(0, "answer", "number", "Add"),
            var(1, "context", "number", "2", "2"),
            var(2, "latent", "number", "Add"),
        ],
        operations=[operation("sum", "Add", "v2", ["v0", "v1"])],
    )
    assert not accepts(t, p)
    assert "operation_0_answer_input_forbidden" in validate(t, json.dumps(p))["issues"]
