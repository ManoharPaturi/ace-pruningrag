"""Immutable closed grammar with captured variable types and conditional operation fields."""

import hashlib
import json

from .query_graph import (
    CLAUSE_FIELDS,
    COMPOSITIONS,
    MAX_CLAUSES,
    MAX_OPERATIONS,
    MAX_VARIABLES,
    OPERATIONS,
    VALUE_TYPES,
    constant_allowed,
    numeric_span,
    operation_types,
    slot_types,
)
from .unicode_claims import permitted_spans


def character_parser(task):
    from lmformatenforcer import CharacterLevelParser

    if task["kind"] != "query":
        raise ValueError("query graph accepts questions only")
    terminal, stop = object(), object()
    cache = {}
    spans = permitted_spans(task["text"])
    anchor_available = isinstance(task.get("query_time"), str) and bool(task["query_time"].strip())

    def tokens(items, next_step):
        key = tuple(raw for raw, _ in items)
        if key not in cache:
            root = {}
            for raw, value in items:
                node = root
                for char in raw:
                    node = node.setdefault(char, {})
                node[terminal] = value
            cache[key] = root
        return cache[key], next_step

    def choices(values, next_step):
        return tokens(
            [(json.dumps(v, ensure_ascii=False, separators=(",", ":")), v) for v in values],
            next_step,
        )

    def literal(raw, next_step):
        return tokens([(raw, None)], lambda _: next_step())

    def fixed(values):
        return lambda data, done: choices(values, done)

    def obj(fields, done):
        def at(index, data):
            if index == len(fields):
                return literal("}", lambda: done(data))
            key, factory = fields[index]
            prefix = ("{" if index == 0 else ",") + json.dumps(key) + ":"
            return literal(prefix, lambda: factory(data, lambda v: at(index + 1, {**data, key: v})))

        return at(0, {})

    def array(factory, maximum, minimum, done):
        def item(values):
            return factory(len(values), values, lambda value: tail((*values, value)))

        def head(values):
            spec = item(values) if len(values) < maximum else ({}, lambda _: None)
            root, continuation = spec
            if len(values) < minimum:
                return spec
            # Stop and item prefixes are disjoint; no parser state or trie is mutated.
            combined = {**root, "]": {terminal: stop}}
            return combined, lambda value: done(values) if value is stop else continuation(value)

        def tail(values):
            def after(delimiter):
                return done(values) if delimiter == "]" else item(values)

            allowed = [("]", "]")] if len(values) >= minimum else []
            if len(values) < maximum and item(values)[0]:
                allowed.append((",", ","))
            return tokens(allowed, after)

        return literal("[", lambda: head(()))

    def variable(index, previous, done):
        kinds = (
            ["answer"]
            if index == 0
            else ["context", "latent", *(["anchor"] if anchor_available else [])]
        )

        def types(v, finish):
            available = ["date"] if v["kind"] == "anchor" else list(VALUE_TYPES)
            if v["kind"] == "context":
                available = [t for t in available if any(constant_allowed(t, s) for s in spans)]
            return choices(available, finish)

        def constant(v, finish):
            available = (
                [s for s in spans if constant_allowed(v["value_type"], s)]
                if v["kind"] == "context"
                else [None]
            )
            return choices(available, finish)

        return obj(
            [
                ("id", fixed([f"v{index}"])),
                ("kind", fixed(kinds)),
                ("value_type", types),
                ("cue", fixed(spans)),
                ("constant", constant),
                (
                    "unit",
                    lambda v, finish: choices(
                        [None, *spans] if v["value_type"] == "number" else [None], finish
                    ),
                ),
            ],
            done,
        )

    def reference(field, variables, statement):
        local = permitted_spans(statement)
        values = [None]
        values.extend(
            {"variable": v["id"]} for v in variables if v["value_type"] in slot_types(field)
        )
        values.extend(
            {"span": s, "value_type": t}
            for t in slot_types(field)
            for s in local
            if constant_allowed(t, s)
        )
        return values

    def clause(index, previous, done, variables):
        fields = []
        for field in CLAUSE_FIELDS:
            if field == "text":
                factory = fixed(spans)
            elif field == "polarity":
                factory = fixed(["positive", "negative", "unknown"])
            elif field in ("relation", "unit", "qualification"):

                def factory(c, finish):
                    return choices([None, *permitted_spans(c["text"])], finish)
            else:

                def factory(c, finish, field=field):
                    return choices(reference(field, variables, c["text"]), finish)

            fields.append((field, factory))
        return obj(fields, done)

    def operation(index, previous, done, variables, clauses):
        by_id = {v["id"]: v for v in variables}
        producers = {o["result"] for o in previous if o["kind"] != "unknown"}
        dependencies = {
            o["result"]: [*o["operands"], *o["candidates"]]
            for o in previous
            if o["kind"] != "unknown"
        }

        def depends(key, target, seen=None):
            if key == target:
                return True
            seen = set() if seen is None else seen
            if key in seen:
                return False
            return any(depends(v, target, seen | {key}) for v in dependencies.get(key, []))

        def inputs(kind, result, args=()):
            types, _, _, _ = operation_types(kind)
            if kind in ("maximum", "minimum"):
                types = (by_id[result]["value_type"],)
            if args and kind != "select":
                types = (by_id[args[0]]["value_type"],)
            return [
                v["id"]
                for v in variables
                if v["id"] != "v0" and not depends(v["id"], result) and v["value_type"] in types
            ]

        def candidates(kind, result, current=()):
            types = (
                (by_id[result]["value_type"],) if not kind.startswith("rank_") else VALUE_TYPES[:-1]
            )
            if current:
                types = (by_id[current[0]]["value_type"],)
            return [
                v["id"]
                for v in variables
                if v["id"] != "v0" and not depends(v["id"], result) and v["value_type"] in types
            ]

        def results(kind):
            _, out_types, minimum, _ = operation_types(kind)
            values = []
            for v in variables:
                key = v["id"]
                if (
                    v["kind"] not in ("answer", "latent")
                    or v["value_type"] not in out_types
                    or key in producers
                ):
                    continue
                if minimum and not inputs(kind, key):
                    continue
                if kind in ("argmax", "argmin", "rank_desc", "rank_asc") and not candidates(
                    kind, key
                ):
                    continue
                values.append(key)
            return values

        meaningful = any(c["subject"] is not None and c["relation"] is not None for c in clauses)
        kinds = [
            "unknown",
            *[
                k
                for k in OPERATIONS
                if k != "unknown" and results(k) and (k != "select" or meaningful or dependencies)
            ],
        ]

        def arguments(o, finish):
            if o["kind"] == "unknown":
                return literal("[]", lambda: finish([]))
            _, _, minimum, maximum = operation_types(o["kind"])
            return array(
                lambda i, current, parsed: choices(inputs(o["kind"], o["result"], current), parsed),
                maximum,
                minimum,
                lambda values: finish(list(values)),
            )

        def candidate_array(o, finish):
            if o["kind"] not in ("argmax", "argmin", "rank_desc", "rank_asc"):
                return literal("[]", lambda: finish([]))
            count = len(o["operands"])
            return array(
                lambda i, current, parsed: choices(
                    candidates(o["kind"], o["result"], current), parsed
                ),
                count,
                count,
                lambda values: finish(list(values)),
            )

        return obj(
            [
                ("kind", fixed(kinds)),
                (
                    "cue",
                    lambda o, finish: choices([None] if o["kind"] == "unknown" else spans, finish),
                ),
                (
                    "result",
                    lambda o, finish: choices(
                        [None] if o["kind"] == "unknown" else results(o["kind"]), finish
                    ),
                ),
                ("operands", arguments),
                ("candidates", candidate_array),
            ],
            done,
        )

    def variables(data, finish):
        return array(
            variable, MAX_VARIABLES if spans else 0, 0, lambda values: finish(list(values))
        )

    def clauses(data, finish):
        return array(
            lambda i, prior, done: clause(i, prior, done, data["variables"]),
            MAX_CLAUSES if spans else 0,
            0,
            lambda values: finish(list(values)),
        )

    def operations(data, finish):
        return array(
            lambda i, prior, done: operation(i, prior, done, data["variables"], data["clauses"]),
            MAX_OPERATIONS,
            0,
            lambda values: finish(list(values)),
        )

    spec = obj(
        [
            ("status", fixed(["partial", "ambiguous"])),
            ("composition", fixed(COMPOSITIONS)),
            ("cardinality", fixed([None, *[s for s in spans if numeric_span(s)]])),
            ("variables", variables),
            ("clauses", clauses),
            ("operations", operations),
        ],
        lambda _: None,
    )

    class ProgramParser(CharacterLevelParser):
        def __init__(self, spec, key):
            super().__init__()
            self.spec, self.key = spec, key

        def get_allowed_characters(self):
            return (
                "" if self.spec is None else "".join(c for c in self.spec[0] if c is not terminal)
            )

        def can_end(self):
            return self.spec is None

        def add_character(self, char):
            if self.spec is None or char not in self.spec[0]:
                raise ValueError("outside typed query graph grammar")
            node = self.spec[0][char]
            key = hashlib.sha256(self.key + char.encode()).digest()
            if terminal in node:
                if len(node) != 1:
                    raise ValueError("ambiguous terminal in typed query grammar")
                return ProgramParser(self.spec[1](node[terminal]), key)
            return ProgramParser((node, self.spec[1]), key)

        def cache_key(self):
            return ("typed_query_graph_v2", self.key)

    return ProgramParser(
        spec,
        hashlib.sha256(
            json.dumps([task["text"], task.get("query_time")], ensure_ascii=False).encode()
        ).digest(),
    )
