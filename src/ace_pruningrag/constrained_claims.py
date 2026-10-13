"""Closed span choices for extraction; structural validity is not semantic truth."""

import json
import re

from .claim_extraction import validate_proposal

FIELDS = ("entity", "relation", "period", "unit", "predicate", "value")


def permitted_spans(text):
    """Every contiguous lexical/punctuation-token range, preserving exact inner text."""
    words = list(re.finditer(r"\S+", text))
    # This is an input cap, not silent span truncation. The 120-word source protocol fits.
    if len(words) > 160:
        raise ValueError("span enumeration exceeds explicit 160-word input cap")
    atoms = list(re.finditer(r"\w+|[^\w\s]", text))
    if len(atoms) > 640:
        raise ValueError("span enumeration exceeds explicit 640-atom input cap")
    return sorted(
        {text[left.start() : right.end()] for i, left in enumerate(atoms) for right in atoms[i:]}
    )


def proposal_schema(task):
    choices = permitted_spans(task["text"])
    field = (
        {"anyOf": [{"type": "string", "enum": choices}, {"type": "null"}]}
        if choices
        else {"type": "null"}
    )
    return {
        "type": "object",
        "properties": {
            name: ({"type": "null"} if task["kind"] == "query" and name == "value" else field)
            for name in FIELDS
        },
        "required": list(FIELDS),
        "additionalProperties": False,
    }


def validate_constrained(task, raw):
    result = validate_proposal(task, raw)
    if result["status"] != "span_bound_proposal":
        return result
    values = json.loads(raw)
    allowed = set(permitted_spans(task["text"]))
    issues = [
        "outside_permitted_token_span_" + name
        for name, value in values.items()
        if value is not None and value not in allowed
    ]
    if issues:
        return {**result, "status": "invalid_constrained_proposal", "issues": issues}
    return {**result, "status": "constrained_span_proposal", "complete_claim_coverage": False}


def character_parser(task):
    from lmformatenforcer import CharacterLevelParser, SequenceParser, StringParser

    # JSON-schema string enums in the pinned library reject some escaped quotes.
    # Compile literal JSON representations instead of dropping legitimate source spans.
    terminal = object()
    trie = {}
    for value in ["null"] + [
        json.dumps(span, ensure_ascii=False) for span in permitted_spans(task["text"])
    ]:
        node = trie
        for char in value:
            node = node.setdefault(char, {})
        node[terminal] = True

    class ClosedChoices(CharacterLevelParser):
        def __init__(self, node):
            super().__init__()
            self.node = node

        def get_allowed_characters(self):
            return "".join(key for key in self.node if key is not terminal)

        def add_character(self, char):
            if char not in self.node:
                raise ValueError("outside closed span grammar")
            return ClosedChoices(self.node[char])

        def can_end(self):
            return terminal in self.node

        def cache_key(self):
            return ("closed_span_node", id(self.node))

    parts = []
    choices = ClosedChoices(trie)
    for index, name in enumerate(FIELDS):
        parts.append(StringParser(("{" if index == 0 else ",") + json.dumps(name) + ":"))
        parts.append(
            StringParser("null") if task["kind"] == "query" and name == "value" else choices
        )
    parts.append(StringParser("}"))
    return SequenceParser(parts)
