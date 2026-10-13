import json

from ace_pruningrag.constrained_claims import permitted_spans as frozen_spans
from ace_pruningrag.unicode_claims import (
    character_parser,
    lexical_spans,
    permitted_spans,
    validate_constrained,
)


def proposal(entity):
    return json.dumps(
        {
            "entity": entity,
            "relation": None,
            "period": None,
            "unit": None,
            "predicate": None,
            "value": None,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def accepts(task, raw):
    parser = character_parser(task)
    for char in raw:
        if char not in parser.get_allowed_characters():
            return False
        parser = parser.add_character(char)
    return parser.can_end()


def test_observed_name_boundary_regression_preserves_frozen_control():
    text = "Victoria Mone\u0301t – WINNER"
    assert "Victoria Mone" in frozen_spans(text)
    assert "Victoria Mone" not in permitted_spans(text)
    assert "Victoria Mone\u0301t" in permitted_spans(text)
    assert "Victoria Monét" not in permitted_spans(text)  # No source normalization.
    task = {"kind": "source", "text": text}
    assert accepts(task, proposal("Victoria Mone\u0301t"))
    assert not accepts(task, proposal("Victoria Mone"))
    assert (
        validate_constrained(task, proposal("Victoria Mone"))["status"]
        == "invalid_constrained_proposal"
    )


def test_multiple_mark_categories_and_exact_offsets():
    for text in ("Cafe\u0301", "a\u20dd", "क\u093e", "o\u0308\u0301"):
        assert lexical_spans(text) == [(0, len(text))]
        assert text in permitted_spans(text)
        assert text[:-1] not in permitted_spans(text)
    text = "Lake\n Powell, 3,531 feet"
    for start, end in lexical_spans(text):
        assert text[start:end]
    assert permitted_spans(text) == frozen_spans(text)
    assert "Lake\n Powell" in permitted_spans(text)


def test_symbol_mark_and_nonacceptance_are_preserved():
    text = "©\ufe0f 2024"
    assert lexical_spans(text) == [(0, 2), (3, 7)]
    result = validate_constrained({"kind": "source", "text": text}, proposal("©\ufe0f"))
    assert result["status"] == "constrained_span_proposal"
    assert not result["answer_accepted"]
    assert not result["semantic_tuple_verified"]


def test_real_token_filter_cannot_close_name_before_combining_suffix():
    from lmformatenforcer import TokenEnforcer, TokenEnforcerTokenizerData

    task = {"kind": "source", "text": "Victoria Mone\u0301t – WINNER"}
    output = proposal("Victoria Mone\u0301t")
    alphabet = sorted(set(output + task["text"]))
    encode = {char: i for i, char in enumerate(alphabet)}
    decode = {i: char for char, i in encode.items()}
    data = TokenEnforcerTokenizerData(
        [(i, char, False) for char, i in encode.items()],
        lambda ids: "".join(decode.get(i, "") for i in ids),
        999,
        False,
        1000,
    )
    enforcer = TokenEnforcer(data, character_parser(task))
    prefix = [998]
    for char in '{"entity":"Victoria Mone':
        assert encode[char] in enforcer.get_allowed_tokens(prefix).allowed_tokens
        prefix.append(encode[char])
    allowed = enforcer.get_allowed_tokens(prefix).allowed_tokens
    assert encode['"'] not in allowed
    assert encode["\u0301"] in allowed
    assert 999 not in allowed
