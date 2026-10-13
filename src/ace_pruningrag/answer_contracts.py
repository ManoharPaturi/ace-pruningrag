"""Conservative query-only constraints; no inference of factual truth or acceptance."""

import hashlib
import json
import re
from datetime import date

from .answer_checks import check_answer_form

_DATE = r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)"


def query_contract(query):
    """Retain explicit spans only; omitted requirements are not assumed absent."""
    requirements = []
    for match in re.finditer(_DATE, query):
        try:
            date.fromisoformat(match.group(1))
        except ValueError:
            continue
        requirements.append(
            {"kind": "date_mention", "value": match.group(1), "span": match.span(1)}
        )
    for kind, pattern in (
        ("decade", r"\b(?:19|20)\d0s\b"),
        ("count", r"\bhow many\b"),
        ("list_size", r"\btop\s+([1-9]\d?)\b"),
        ("price_field", r"\b(?:opening|closing)\s+(?:stock\s+)?price\b"),
        ("negative_eligibility", r"\b(?:never|without|not)\b"),
        ("relative_time", r"\b(?:latest|current|today|yesterday)\b"),
    ):
        for match in re.finditer(pattern, query, re.I):
            value = match.group(1) if kind == "list_size" else match.group().casefold()
            requirements.append({"kind": kind, "value": value, "span": match.span()})
    return {
        "schema_version": 1,
        "query_sha256": hashlib.sha256(query.encode()).hexdigest(),
        "requirements": requirements,
        "coverage": "partial_explicit_spans",
        "unresolved_fields": ["entity_role", "relation", "unit", "claim_support", "completeness"],
    }


def diagnose_contract(query, prediction, evidence_ids=()):
    """Flag explicit scope conflicts; never accept an answer from these checks."""
    evidence_ids = tuple(evidence_ids)
    contract = query_contract(query)
    form = check_answer_form(query, prediction, evidence_ids)
    findings = [{"code": code, "basis": "answer_form"} for code in form["issues"]]
    requirements = contract["requirements"]
    decades = {r["value"] for r in requirements if r["kind"] == "decade"}
    # Quotes, negation, comparisons or multiple scopes cannot be reliably attributed.
    ambiguous = bool(
        re.search(r"[\"“”]|\b(?:not|rather|instead|versus|vs|but)\b", prediction, re.I)
    )
    if not ambiguous and len(decades) == 1 and not re.search(r"\ball[- ]time\b", query, re.I):
        if re.search(r"\ball[- ]time\b", prediction, re.I) and not any(
            decade in prediction.casefold() for decade in decades
        ):
            findings.append({"code": "explicit_all_time_for_decade", "basis": "answer_scope"})
    fields = {r["value"].split()[0] for r in requirements if r["kind"] == "price_field"}
    query_ambiguous = bool(re.search(r"\b(?:not|compare|versus|vs|rather|instead)\b", query, re.I))
    if not ambiguous and not query_ambiguous and len(fields) == 1:
        requested = next(iter(fields))
        opposite = "closing" if requested == "opening" else "opening"
        if re.search(rf"\b{opposite}\s+(?:stock\s+)?price\b", prediction, re.I) and not re.search(
            rf"\b{requested}\s+(?:stock\s+)?price\b", prediction, re.I
        ):
            findings.append({"code": "explicit_opposite_price_field", "basis": "answer_scope"})
    # Date mentions alone do not define a target: require one explicit 'on DATE' request
    # and one explicit 'as of DATE' answer; multi-date comparisons stay unresolved.
    dates = [r["value"] for r in requirements if r["kind"] == "date_mention"]
    answer_dates = re.findall(_DATE, prediction)
    if not ambiguous and not query_ambiguous and len(dates) == len(answer_dates) == 1:
        if re.search(rf"\bon\s+{re.escape(dates[0])}\b", query, re.I) and re.search(
            rf"\bas of\s+{re.escape(answer_dates[0])}\b", prediction, re.I
        ):
            try:
                date.fromisoformat(answer_dates[0])
            except ValueError:
                pass
            else:
                if dates[0] != answer_dates[0]:
                    findings.append(
                        {"code": "explicit_answer_date_mismatch", "basis": "answer_scope"}
                    )
    status = "unresolved"
    if form["status"] == "generator_abstained":
        status = "generator_abstained"
    elif findings:
        status = "review_required"
    binding = {"query": query, "prediction": prediction, "evidence_ids": list(evidence_ids)}
    return {
        "contract": contract,
        "binding_sha256": hashlib.sha256(json.dumps(binding, sort_keys=True).encode()).hexdigest(),
        "status": status,
        "findings": findings,
        "answer_accepted": False,
        "factual_correctness_verified": False,
        "claim_support_verified": False,
    }
