import json

from ace_pruningrag.claim_inventory import FIELDS, MAX_FRAMES, character_parser


def raw(statement, **values):
    frame = {key: (statement if key == "statement" else values.get(key)) for key in FIELDS}
    return json.dumps(
        {"inventory_status": "partial", "frames": [frame]},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def accepts(task, output):
    parser = character_parser(task)
    for char in output:
        if char not in parser.get_allowed_characters():
            return False
        parser = parser.add_character(char)
    return parser.can_end()


def test_closed_inventory_lists_quotes_unicode_and_query_answer_exclusion():
    task = {"kind": "query", "text": 'Who plays Café "X"?'}
    output = raw(task["text"], subject='Café "X"', relation="plays")
    assert accepts(task, output)
    assert not accepts(task, raw(task["text"], value="Café"))
    assert not accepts(task, raw(task["text"], subject="Invented actor"))
    for text in ("Victoria Mone\u0301t won.", 'A said "yes".'):
        source = {"kind": "source", "text": text}
        assert accepts(source, raw(text, subject=text))
    source = {"kind": "source", "text": "Victoria Mone\u0301t won."}
    assert not accepts(source, raw(source["text"], subject="Victoria Mone"))


def test_zero_through_twelve_frames_and_full_object_termination():
    task = {"kind": "source", "text": "A won."}
    frame = json.loads(raw(task["text"]))["frames"][0]
    for count in (0, 1, 2, MAX_FRAMES):
        output = json.dumps(
            {"inventory_status": "partial", "frames": [frame] * count},
            separators=(",", ":"),
        )
        assert accepts(task, output)  # Duplicate rejection belongs to the separate validator.
        assert not accepts(task, output[:-1])
    output = json.dumps(
        {"inventory_status": "partial", "frames": [frame] * (MAX_FRAMES + 1)},
        separators=(",", ":"),
    )
    assert not accepts(task, output)
    assert accepts({"kind": "source", "text": ""}, '{"inventory_status":"partial","frames":[]}')


def test_real_token_filter_disallows_early_terminator_and_accepts_complete_inventory():
    from lmformatenforcer import TokenEnforcer, TokenEnforcerTokenizerData

    task = {"kind": "source", "text": 'A said "yes".'}
    output = raw(task["text"], subject="A", relation="said", value='"yes"')
    alphabet = sorted(set(output + task["text"]))
    encode = {char: i for i, char in enumerate(alphabet)}
    decode = {i: char for char, i in encode.items()}
    data = TokenEnforcerTokenizerData(
        [(i, c, False) for c, i in encode.items()],
        lambda ids: "".join(decode.get(i, "") for i in ids),
        999,
        False,
        1000,
    )
    enforcer = TokenEnforcer(data, character_parser(task))
    prefix = [998]
    for char in output:
        allowed = enforcer.get_allowed_tokens(prefix).allowed_tokens
        assert encode[char] in allowed
        assert 999 not in allowed
        prefix.append(encode[char])
    assert 999 in enforcer.get_allowed_tokens(prefix).allowed_tokens
