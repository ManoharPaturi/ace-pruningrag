from ace_pruningrag.answer_checks import check_answer_form, rectangle_calculation


def test_identifiers_are_flagged_but_legitimate_identifier_requests_are_preserved():
    identifier = "a" * 64
    assert check_answer_form("How many units?", f"`{identifier}`", [identifier])["issues"] == [
        "provenance_identifier_as_answer"
    ]
    assert not check_answer_form("What is the evidence identifier?", identifier, [identifier])[
        "issues"
    ]
    assert not check_answer_form("Name the actor", "An Actor", [identifier])[
        "factual_correctness_verified"
    ]


def test_numbered_list_requires_complete_contiguous_unique_items():
    query = "What are the top 3 holdings?"
    assert not check_answer_form(query, "1. A\n2. B\n3. C", [])["issues"]
    assert (
        "requested_list_cardinality_or_numbering_mismatch"
        in check_answer_form(query, "1. A\n3. C", [])["issues"]
    )
    assert "duplicate_list_items" in check_answer_form(query, "1. A\n2. A\n3. B", [])["issues"]
    assert check_answer_form(query, "A, B, C", [])["issues"] == ["requested_list_unparsed"]
    assert check_answer_form(query, "I don't know.", [])["status"] == "generator_abstained"


def test_decimal_arithmetic_units_and_unsupported_geometry():
    query = "What is the area of a rectangle 2.5 meters by 4 metres?"
    assert rectangle_calculation(query)["value"] == "10.0"
    assert not check_answer_form(query, "10 m²", [])["issues"]
    assert check_answer_form(query, "9 m²", [])["issues"] == ["area_arithmetic_mismatch"]
    assert check_answer_form(query, "10 ft²", [])["issues"] == ["area_unit_mismatch"]
    assert check_answer_form(query, "It might be 10 m² or 12 m²", [])["issues"] == [
        "area_answer_unparsed"
    ]
    for q in (
        "Area of a room 17 meters by 66 meters?",
        "Area of a non rectangular room 2 meters by 3 meters?",
        "Area of a rectangle 2 feet by 3 meters?",
        "Area of a rectangle 0 meters by 3 meters?",
        "Area of a rectangle -2 meters by 3 meters?",
        "Area of two rectangles 2 meters by 3 meters and 4 meters by 5 meters?",
    ):
        assert rectangle_calculation(q) is None
