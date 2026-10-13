import json

from ace_pruningrag.claim_alignment import compare_proposals
from ace_pruningrag.claim_extraction import validate_proposal


def proposal(kind, text, **values):
    keys = ("entity", "relation", "period", "unit", "predicate", "value")
    return validate_proposal(
        {"kind": kind, "text": text}, json.dumps({k: values.get(k) for k in keys})
    )


def test_explicit_entity_relation_period_unit_bindings_do_not_accept():
    query = proposal(
        "query", "A earned USD in 2022", entity="A", relation="earned", unit="USD", period="2022"
    )
    source = proposal(
        "source",
        "A earned USD 7 in 2022",
        entity="A",
        relation="earned",
        unit="USD",
        period="2022",
        value="7",
    )
    result = compare_proposals(query, source)
    assert result["status"] == "literal_fields_aligned"
    assert not result["semantic_support_verified"]
    assert not result["answer_accepted"]
    wrong = proposal(
        "source",
        "A earned EUR 7 in 2023",
        entity="A",
        relation="earned",
        unit="EUR",
        period="2023",
        value="7",
    )
    result = compare_proposals(query, wrong)
    assert result["status"] == "different_explicit_fields"
    assert not result["field_comparisons"]["unit"]["literal_equal"]
    assert not result["field_comparisons"]["period"]["literal_equal"]


def test_missing_repeated_and_paraphrased_fields_are_not_guessed():
    query = proposal(
        "query", "A earned USD in 2022", entity="A", relation="earned", unit="USD", period="2022"
    )
    for source in (
        proposal("source", "A earned 7", entity="A", relation="earned", value="7"),
        proposal(
            "source",
            "A earned USD 7 in 2022. A",
            entity="A",
            relation="earned",
            unit="USD",
            period="2022",
            value="7",
        ),
        {"status": "invalid_json"},
    ):
        assert compare_proposals(query, source)["status"] == "unresolved"
    synonym = proposal(
        "source",
        "A made USD 7 in 2022",
        entity="A",
        relation="made",
        unit="USD",
        period="2022",
        value="7",
    )
    assert compare_proposals(query, synonym)["status"] == "different_explicit_fields"
