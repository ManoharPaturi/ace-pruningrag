import json

import pytest

from ace_pruningrag.constrained_claims import (
    FIELDS,
    character_parser,
    permitted_spans,
    validate_constrained,
)


def accepts(task, raw):
    parser = character_parser(task)
    for char in raw:
        if char not in parser.get_allowed_characters():
            return False
        parser = parser.add_character(char)
    return parser.can_end()


def raw(**values):
    return json.dumps({k: values.get(k) for k in FIELDS}, ensure_ascii=False, separators=(",", ":"))


def test_permitted_spans_preserve_whitespace_unicode_and_input_cap():
    text = "Lake\n Powell 3,531 feet"
    assert "Lake\n Powell" in permitted_spans(text)
    assert "Lake Powell" not in permitted_spans(text)
    assert "531" in permitted_spans(text)
    assert "Caf" not in permitted_spans("Café")
    with pytest.raises(ValueError, match="cap"):
        permitted_spans("x " * 161)


def test_real_character_parser_rejects_hallucinations_schema_and_query_answers():
    task = {"kind": "query", "text": "Who plays Harvey Specter?"}
    assert accepts(task, raw(entity="Harvey Specter", relation="plays"))
    for bad in (
        raw(entity="Gabriel Macht"),
        raw(value="Harvey Specter?"),
        raw(period="2024"),
        raw(unit="null"),
        '{"entity":null}',
        raw()[:-1] + ',"extra":null}',
        "```json\n" + raw(),
    ):
        assert not accepts(task, bad)
    assert not accepts(
        task,
        '{"relation":null,"entity":null,"period":null,"unit":null,"predicate":null,"value":null}',
    )


def test_escaped_quotes_unicode_and_repeated_text_do_not_enable_acceptance():
    task = {"kind": "source", "text": 'A said "yes". Café earned €2.'}
    output = raw(entity="Café", relation="earned", value="€2.")
    assert accepts(task, output)
    assert accepts(task, raw(entity='"yes".'))
    result = validate_constrained(task, output)
    assert result["status"] == "constrained_span_proposal"
    assert not result["answer_accepted"]
    assert not result["semantic_tuple_verified"]
    assert not result["complete_claim_coverage"]
    partial = raw(entity="Caf")
    assert not accepts(task, partial)
    assert validate_constrained(task, partial)["status"] == "invalid_constrained_proposal"


def test_real_token_enforcer_only_allows_complete_closed_outputs():
    from lmformatenforcer import TokenEnforcer, TokenEnforcerTokenizerData

    task = {"kind": "query", "text": 'Who plays Café "X"?'}
    output = raw(entity="Café", relation="plays")
    alphabet = sorted(set(output + task["text"] + "\\n"))
    encoded = {char: i for i, char in enumerate(alphabet)}
    decoded = {i: char for char, i in encoded.items()}
    data = TokenEnforcerTokenizerData(
        [(i, char, False) for char, i in encoded.items()],
        lambda ids: "".join(decoded.get(i, "") for i in ids),
        999,
        False,
        1000,
    )
    enforcer = TokenEnforcer(data, character_parser(task))
    prefix = [998]  # A prompt sentinel is not generated output.
    for char in output:
        allowed = enforcer.get_allowed_tokens(prefix).allowed_tokens
        assert 999 not in allowed
        assert encoded[char] in allowed
        prefix.append(encoded[char])
    assert 999 in enforcer.get_allowed_tokens(prefix).allowed_tokens


def test_pinned_schema_enum_quote_limitation_does_not_drop_legitimate_choices():
    from lmformatenforcer import CharacterLevelParserConfig, JsonSchemaParser

    from ace_pruningrag.constrained_claims import proposal_schema

    task = {"kind": "source", "text": 'A said "yes".'}
    output = raw(entity='"yes".')
    parser = JsonSchemaParser(
        proposal_schema(task), config=CharacterLevelParserConfig(force_json_field_order=True)
    )
    rejected = False
    for char in output:
        if char not in parser.get_allowed_characters():
            rejected = True
            break
        parser = parser.add_character(char)
    assert rejected
    assert accepts(task, output)
