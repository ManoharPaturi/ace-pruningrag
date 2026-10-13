"""Compare literal proposed fields without treating span validity as entailment."""

import re


def _key(text):
    return re.sub(r"\s+", " ", text).strip().casefold()


def compare_proposals(requirement, claim):
    """Expose exact field matches/mismatches; no aliasing or factual acceptance."""
    result = {
        "status": "unresolved",
        "field_comparisons": {},
        "missing_fields": [],
        "ambiguous_fields": [],
        "semantic_support_verified": False,
        "answer_accepted": False,
    }
    if any(p.get("status") != "span_bound_proposal" for p in (requirement, claim)):
        result["reason"] = "invalid_extraction"
        return result
    requested, asserted = requirement["fields"], claim["fields"]
    for name in ("entity", "relation", "period", "unit", "predicate"):
        left, right = requested.get(name), asserted.get(name)
        if left is None:
            if name in ("entity", "relation"):
                result["missing_fields"].append("query_" + name)
            continue
        if right is None:
            result["missing_fields"].append("source_" + name)
            continue
        if len(left["spans"]) != 1 or len(right["spans"]) != 1:
            result["ambiguous_fields"].append(name)
        result["field_comparisons"][name] = {
            "query_text": left["text"],
            "source_text": right["text"],
            "literal_equal": _key(left["text"]) == _key(right["text"]),
        }
    value = asserted.get("value")
    if value is None:
        result["missing_fields"].append("source_value")
    elif len(value["spans"]) != 1:
        result["ambiguous_fields"].append("value")
    if result["missing_fields"] or result["ambiguous_fields"]:
        result["reason"] = "incomplete_or_ambiguous_proposed_fields"
    elif all(field["literal_equal"] for field in result["field_comparisons"].values()):
        result["status"] = "literal_fields_aligned"
        result["reason"] = "Semantic tuple, scope completeness and truth remain unverified."
    else:
        result["status"] = "different_explicit_fields"
        result["reason"] = (
            "Different strings may be aliases or paraphrases; no unsupported verdict."
        )
    return result
