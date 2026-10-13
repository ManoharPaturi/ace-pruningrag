"""Query-only answer-form checks and explicit rectangle arithmetic diagnostics.

These checks preserve raw answers. Passing a form check is not factual or citation
verification, and unparsed text is unresolved rather than automatically incorrect.
"""

import re
from decimal import Decimal, localcontext


def rectangle_calculation(query):
    """Calculate only an explicitly rectangular area with two compatible lengths."""
    if not re.search(r"\barea\b", query, re.I) or not re.search(
        r"\b(?:rectangle|rectangular)\b", query, re.I
    ):
        return None
    if re.search(r"\b(?:not|non|irregular|triangle|circle)\b", query, re.I):
        return None
    number = r"(?:\d{1,8}(?:\.\d{1,8})?)"
    unit = r"(?:meters?|metres?|feet|foot|inches?|centimeters?|centimetres?)"
    matches = list(
        re.finditer(
            rf"(?<![\w.+-])({number})\s+({unit})\s+by\s+({number})\s+({unit})\b",
            query,
            re.I,
        )
    )
    if len(matches) != 1:
        return None
    left, left_unit, right, right_unit = matches[0].groups()
    units = {
        "meter": "m",
        "meters": "m",
        "metre": "m",
        "metres": "m",
        "feet": "ft",
        "foot": "ft",
        "inch": "in",
        "inches": "in",
        "centimeter": "cm",
        "centimeters": "cm",
        "centimetre": "cm",
        "centimetres": "cm",
    }
    if units[left_unit.lower()] != units[right_unit.lower()]:
        return None
    a, b = Decimal(left), Decimal(right)
    if a <= 0 or b <= 0:
        return None
    with localcontext() as context:
        context.prec = 64
        product = str(a * b)
    return {
        "operation": "rectangle_area",
        "operands": [left, right],
        "value": product,
        "unit": units[left_unit.lower()] + "²",
        "query_span": matches[0].group(),
        "assumptions": "The query explicitly states rectangular geometry.",
    }


def check_answer_form(query, prediction, selected_evidence_ids):
    """Flag a narrow observable form failure without modifying the generator answer."""
    text = prediction.strip()
    issues = []
    evidence_ids = set(selected_evidence_ids)
    # Citation-looking wrapping does not turn an identifier into a substantive answer.
    identifier = text.strip("`[]\"' .")
    asks_identifier = bool(re.search(r"\b(?:hash|sha256|identifier|evidence\s+id)\b", query, re.I))
    if not text:
        issues.append("empty_answer")
    elif identifier in evidence_ids and not asks_identifier:
        issues.append("provenance_identifier_as_answer")
    if text.casefold() in {"i don't know", "i don't know.", "i do not know", "i do not know."}:
        return {
            "status": "generator_abstained",
            "issues": [],
            "calculation": None,
            "factual_correctness_verified": False,
            "claim_support_verified": False,
        }
    requested = re.search(r"\btop\s+([1-9]\d?)\s+", query, re.I)
    if requested and not asks_identifier:
        count = int(requested.group(1))
        items = re.findall(r"^\s*(\d{1,2})[.)]\s+(.+?)\s*$", text, re.M)
        if not items:
            issues.append("requested_list_unparsed")
        else:
            indices = [int(index) for index, _ in items]
            if indices != list(range(1, count + 1)):
                issues.append("requested_list_cardinality_or_numbering_mismatch")
            if len({item.casefold() for _, item in items}) != len(items):
                issues.append("duplicate_list_items")
    calculation = rectangle_calculation(query)
    if calculation is not None:
        scalar = re.fullmatch(r"([+]?(?:\d+(?:\.\d*)?|\.\d+))\s*(m²|ft²|in²|cm²)", text)
        if scalar is None:
            issues.append("area_answer_unparsed")
        elif scalar.group(2) != calculation["unit"]:
            issues.append("area_unit_mismatch")
        elif Decimal(scalar.group(1)) != Decimal(calculation["value"]):
            issues.append("area_arithmetic_mismatch")
    return {
        "status": "issues_detected" if issues else "no_form_issue_detected",
        "issues": issues,
        "calculation": calculation,
        "factual_correctness_verified": False,
        "claim_support_verified": False,
    }
