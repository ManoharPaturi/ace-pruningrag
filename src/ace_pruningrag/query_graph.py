"""Typed query proposals; argument positions belong to clauses, not global variables."""

import json
import re
from itertools import combinations

from .query_requirements import _spans
from .unicode_claims import permitted_spans

MAX_VARIABLES, MAX_CLAUSES, MAX_OPERATIONS = 8, 12, 8
VALUE_TYPES = (
    "entity",
    "number",
    "date",
    "period",
    "boolean",
    "set",
    "text",
    "comparison",
    "unknown",
)
KINDS = ("answer", "context", "latent", "anchor")
COMPOSITIONS = ("all", "any", "comparison", "rank", "calculation", "unknown")
OPERATIONS = (
    "select",
    "count",
    "greater",
    "less",
    "equal",
    "not_equal",
    "difference",
    "sum",
    "product",
    "quotient",
    "mean",
    "maximum",
    "minimum",
    "age_years",
    "argmax",
    "argmin",
    "rank_desc",
    "rank_asc",
    "unknown",
)
CLAUSE_FIELDS = (
    "text",
    "subject",
    "relation",
    "polarity",
    "object",
    "value",
    "unit",
    "period",
    "qualification",
)
VARIABLE_FIELDS = ("id", "kind", "value_type", "cue", "constant", "unit")
OPERATION_FIELDS = ("kind", "cue", "result", "operands", "candidates")
NUMBER_WORDS = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
    "hundred",
    "thousand",
    "million",
    "billion",
)


def numeric_span(value):
    if not isinstance(value, str):
        return False
    return (
        bool(
            re.fullmatch(
                r"[+-]?(?:\d+(?:,\d{3})*)(?:\.\d+)?(?:[eE][+-]?\d+)?"
                r"(?: (?:thousand|million|billion))?",
                value,
            )
        )
        or value.casefold() in NUMBER_WORDS
    )


def date_span(value):
    return isinstance(value, str) and bool(
        re.fullmatch(
            r"(?:\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}/\d{1,2}/\d{4}|"
            r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
            r"(?: \d{1,2},?)?(?: \d{4})?)",
            value,
            re.I,
        )
    )


def period_span(value):
    return isinstance(value, str) and (
        date_span(value)
        or bool(
            re.fullmatch(
                r"(?:\d{4}s|today|yesterday|tomorrow|now|currently|current|at the moment|"
                r"(?:last|this|next|previous|past) (?:day|week|month|quarter|year|decade|time)|"
                r"(?:the )?\d{4}s|(?:from |in |as of )?\d{4})",
                value,
                re.I,
            )
        )
    )


def constant_allowed(value_type, value):
    if value_type == "number":
        return numeric_span(value)
    if value_type == "date":
        return date_span(value)
    if value_type == "period":
        return period_span(value)
    if value_type == "boolean":
        return isinstance(value, str) and value.casefold() in ("true", "false", "yes", "no")
    return isinstance(value, str) and bool(value)


def slot_types(field):
    if field in ("subject", "object"):
        return ("entity", "set", "text", "unknown")
    if field == "period":
        return ("date", "period", "unknown")
    return VALUE_TYPES


def operation_types(kind):
    if kind in ("sum", "product"):
        return ("number",), ("number",), 2, MAX_VARIABLES
    if kind == "quotient":
        return ("number",), ("number",), 2, 2
    if kind == "mean":
        return ("number",), ("number",), 1, MAX_VARIABLES
    if kind in ("maximum", "minimum"):
        return ("number", "date"), ("number", "date"), 1, MAX_VARIABLES
    if kind == "age_years":
        return ("date",), ("number",), 2, 2
    if kind == "difference":
        return ("number", "date"), ("number",), 2, 2
    if kind == "count":
        return ("set",), ("number",), 1, 1
    if kind in ("greater", "less", "equal", "not_equal"):
        return (
            (("number", "date") if kind in ("greater", "less") else VALUE_TYPES[:-1]),
            (
                "boolean",
                "comparison",
            ),
            2,
            2,
        )
    if kind in ("argmax", "argmin", "rank_desc", "rank_asc"):
        return (
            ("number", "date"),
            ("set",) if kind.startswith("rank_") else VALUE_TYPES[:-1],
            1,
            MAX_VARIABLES,
        )
    return VALUE_TYPES, VALUE_TYPES, 0, MAX_VARIABLES


def validate(task, raw):
    if task["kind"] != "query":
        raise ValueError("query graph accepts questions only")
    flags = {
        "semantic_requirements_verified": False,
        "full_requirement_coverage_verified": False,
        "answer_acceptance_enabled": False,
        "query_time_anchor": task.get("query_time"),
    }
    try:
        p = json.loads(raw)
    except (ValueError, TypeError):
        return {**flags, "status": "invalid_json", "issues": ["invalid_json"], "warnings": []}
    if (
        not isinstance(p, dict)
        or set(p) != {"status", "composition", "cardinality", "variables", "clauses", "operations"}
        or p["status"] not in ("partial", "ambiguous")
        or p["composition"] not in COMPOSITIONS
        or any(
            not isinstance(p[k], list) or len(p[k]) > cap
            for k, cap in (
                ("variables", MAX_VARIABLES),
                ("clauses", MAX_CLAUSES),
                ("operations", MAX_OPERATIONS),
            )
        )
    ):
        return {**flags, "status": "invalid_schema", "issues": ["invalid_schema"], "warnings": []}
    allowed, issues, warnings = set(permitted_spans(task["text"])), [], []

    def bind(value, label, clause=None):
        if value is None:
            return None
        if not isinstance(value, str) or not value or value not in allowed:
            issues.append("unbound_" + label)
            return None
        spans = _spans(task["text"], value)
        if clause is not None:
            spans = sorted(
                {
                    (a + c, a + d)
                    for a, _ in _spans(task["text"], clause)
                    for c, d in _spans(clause, value)
                }
            )
        if not spans:
            issues.append("outside_clause_" + label)
        return {"text": value, "spans": [list(s) for s in spans]}

    if p["cardinality"] is not None and not numeric_span(p["cardinality"]):
        issues.append("cardinality_not_numeric_span")
    cardinality = bind(p["cardinality"], "cardinality")
    variables = {}
    for i, v in enumerate(p["variables"]):
        if (
            not isinstance(v, dict)
            or set(v) != set(VARIABLE_FIELDS)
            or v["id"] != f"v{i}"
            or v["kind"] not in KINDS
            or v["value_type"] not in VALUE_TYPES
        ):
            issues.append(f"variable_{i}_schema")
            continue
        if (i == 0 and v["kind"] != "answer") or (i > 0 and v["kind"] == "answer"):
            issues.append("exactly_one_first_answer_variable")
        if v["cue"] is None:
            issues.append(f"variable_{i}_cue_missing")
        if v["kind"] != "context" and v["constant"] is not None:
            issues.append(f"variable_{i}_unknown_assignment_forbidden")
        if v["kind"] == "context" and not constant_allowed(v["value_type"], v["constant"]):
            issues.append(f"variable_{i}_constant_type")
        if v["kind"] == "anchor" and (
            v["value_type"] != "date"
            or not isinstance(task.get("query_time"), str)
            or not task["query_time"].strip()
        ):
            issues.append(f"variable_{i}_query_time_anchor_unavailable")
        if v["unit"] is not None and v["value_type"] != "number":
            issues.append(f"variable_{i}_unit_on_nonnumeric_type")
        if v["value_type"] == "unknown":
            warnings.append(f"variable_{i}_type_unresolved")
        variables[v["id"]] = {
            **v,
            "cue_binding": bind(v["cue"], f"variable_{i}_cue"),
            "constant_binding": bind(v["constant"], f"variable_{i}_constant"),
            "unit_binding": bind(v["unit"], f"variable_{i}_unit"),
        }
    used, graph, fact_variables, clauses = set(), {v: set() for v in variables}, set(), []

    def connect(ids):
        for a, b in combinations(ids, 2):
            graph[a].add(b)
            graph[b].add(a)

    for i, c in enumerate(p["clauses"]):
        if (
            not isinstance(c, dict)
            or set(c) != set(CLAUSE_FIELDS)
            or not isinstance(c["text"], str)
            or not c["text"]
        ):
            issues.append(f"clause_{i}_schema")
            continue
        statement = c["text"]
        if c["polarity"] not in ("positive", "negative", "unknown"):
            issues.append(f"clause_{i}_polarity")
        if c["polarity"] == "unknown":
            warnings.append(f"clause_{i}_polarity_unresolved")
        bound, refs = {"text": bind(statement, f"clause_{i}_text")}, set()
        for field in CLAUSE_FIELDS[1:]:
            value, label = c[field], f"clause_{i}_{field}"
            if field == "polarity":
                bound[field] = value
            elif field in ("relation", "unit", "qualification"):
                bound[field] = bind(value, label, statement)
            elif value is None:
                bound[field] = None
            elif isinstance(value, dict) and set(value) == {"variable"}:
                key = value["variable"]
                if not isinstance(key, str) or key not in variables:
                    issues.append("undeclared_" + label)
                elif variables[key]["value_type"] not in slot_types(field):
                    issues.append("inconsistent_type_" + label)
                else:
                    refs.add(key)
                bound[field] = value
            elif isinstance(value, dict) and set(value) == {"span", "value_type"}:
                if value["value_type"] == "unknown":
                    warnings.append("literal_type_unresolved_" + label)
                if value["value_type"] not in slot_types(field) or not constant_allowed(
                    value["value_type"], value["span"]
                ):
                    issues.append("inconsistent_literal_type_" + label)
                bound[field] = bind(value["span"], label, statement)
            else:
                issues.append("invalid_reference_" + label)
        if c["subject"] is None or c["relation"] is None:
            warnings.append(f"clause_{i}_unlinked")
        else:
            fact_variables.update(refs)
            used.update(refs)
            connect(refs)
        clauses.append(bound)
    operations, producers, dependencies, substantive = [], {}, {}, False
    for i, op in enumerate(p["operations"]):
        if (
            not isinstance(op, dict)
            or set(op) != set(OPERATION_FIELDS)
            or op["kind"] not in OPERATIONS
            or any(
                not isinstance(op[k], list) or len(op[k]) > MAX_VARIABLES
                for k in ("operands", "candidates")
            )
        ):
            issues.append(f"operation_{i}_schema")
            continue
        kind, result, args, candidates = op["kind"], op["result"], op["operands"], op["candidates"]
        bound = {**op, "cue_binding": bind(op["cue"], f"operation_{i}_cue")}
        operations.append(bound)
        if kind == "unknown":
            if op["cue"] is not None or result is not None or args or candidates:
                issues.append(f"operation_{i}_unknown_must_be_empty")
            warnings.append(f"operation_{i}_unresolved")
            continue
        if op["cue"] is None:
            issues.append(f"operation_{i}_missing_cue")
        if not isinstance(result, str) or result not in variables:
            issues.append(f"operation_{i}_missing_or_undeclared_result")
            continue
        input_types, output_types, minimum, maximum = operation_types(kind)
        if (
            variables[result]["kind"] not in ("answer", "latent")
            or variables[result]["value_type"] not in output_types
        ):
            issues.append(f"operation_{i}_result_type_or_assignment")
        if result in producers:
            issues.append(f"operation_{i}_duplicate_producer")
        producers[result] = i
        ids = [*args, *candidates]
        if any(not isinstance(v, str) or v not in variables for v in ids):
            issues.append(f"operation_{i}_undeclared_input")
            continue
        if result in ids:
            issues.append(f"operation_{i}_self_dependency")
        if "v0" in ids:
            issues.append(f"operation_{i}_answer_input_forbidden")
        if not minimum <= len(args) <= maximum:
            issues.append(f"operation_{i}_arity")
        types = {variables[v]["value_type"] for v in args}
        if any(t not in input_types for t in types) or (kind != "select" and len(types) > 1):
            issues.append(f"operation_{i}_operand_type")
        if (
            kind in ("maximum", "minimum")
            and types
            and variables[result]["value_type"] not in types
        ):
            issues.append(f"operation_{i}_result_operand_type")
        ranking = kind in ("argmax", "argmin", "rank_desc", "rank_asc")
        if ranking:
            if len(candidates) != len(args):
                issues.append(f"operation_{i}_candidate_arity")
            if len({variables[v]["value_type"] for v in candidates}) > 1:
                issues.append(f"operation_{i}_candidate_type_mismatch")
            if any(variables[v]["value_type"] == "unknown" for v in candidates):
                warnings.append(f"operation_{i}_candidate_type_unresolved")
            if not kind.startswith("rank_") and any(
                variables[v]["value_type"] != variables[result]["value_type"] for v in candidates
            ):
                issues.append(f"operation_{i}_candidate_result_type")
        elif candidates:
            issues.append(f"operation_{i}_unexpected_candidates")
        dependencies[result] = ids
        used.update([result, *ids])
        connect(set([result, *ids]))
        substantive |= kind != "select"
    visiting, visited = set(), set()

    def visit(key):
        if key in visiting:
            return True
        if key in visited:
            return False
        visiting.add(key)
        cyclic = any(visit(v) for v in dependencies.get(key, []) if v in dependencies)
        visiting.remove(key)
        visited.add(key)
        return cyclic

    if any(visit(v) for v in dependencies):
        issues.append("operation_dependency_cycle")
    if "v0" not in variables:
        warnings.append("missing_answer_variable")
    reachable, pending = set(), ["v0"] if "v0" in variables else []
    while pending:
        key = pending.pop()
        if key in reachable:
            continue
        reachable.add(key)
        pending.extend(graph[key] - reachable)
    for key, v in variables.items():
        if key not in used or key not in reachable:
            warnings.append("unlinked_variable_" + key)
        if v["kind"] == "latent" and key not in producers and key not in fact_variables:
            warnings.append("unconstrained_latent_" + key)
    if not fact_variables and not substantive:
        warnings.append("no_meaningful_requirement_links")
    if p["composition"] in ("comparison", "rank", "calculation") and not substantive:
        warnings.append("required_operation_unresolved")
    if p["status"] == "ambiguous":
        warnings.append("query_intent_ambiguous")
    consumed = {v for values in dependencies.values() for v in values}
    for key in producers:
        if key != "v0" and key not in consumed and key not in fact_variables:
            warnings.append("unused_operation_result_" + key)
    return {
        **flags,
        "status": "invalid_requirement_graph"
        if issues
        else "unresolved_requirement_graph"
        if warnings
        else "linked_requirement_graph",
        "status_proposal": p["status"],
        "composition_proposal": p["composition"],
        "cardinality": cardinality,
        "variables": variables,
        "clauses": clauses,
        "operations": operations,
        "issues": issues,
        "warnings": warnings,
    }
