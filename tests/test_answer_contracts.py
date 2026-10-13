from ace_pruningrag.answer_contracts import diagnose_contract, query_contract


def codes(query, answer):
    result = diagnose_contract(query, answer)
    assert not result["answer_accepted"]
    assert not result["factual_correctness_verified"]
    return {f["code"] for f in result["findings"]}


def test_query_only_spans_and_ambiguous_dates():
    query = "How many wins in the 1980s, not counting playoffs on 2020-02-30?"
    contract = query_contract(query)
    assert not any(r["kind"] == "date_mention" for r in contract["requirements"])
    for requirement in contract["requirements"]:
        a, b = requirement["span"]
        assert query[a:b].casefold() == requirement["value"]
    assert "claim_support" in contract["unresolved_fields"]


def test_explicit_scope_conflicts_and_negation_controls():
    q = "How many championships in the 1980s?"
    assert "explicit_all_time_for_decade" in codes(q, "Their all-time total is 12.")
    for answer in ("They won 2.", "Not the all-time total: 2.", "All-time 12, but 2 in the 1980s."):
        assert not codes(q, answer)
    assert not codes("Compare all-time and 1980s totals", "All-time total: 12")
    assert not codes("Compare 1980s and 1990s totals", "All-time total: 12")


def test_explicit_price_and_date_conflicts_not_bare_values():
    q = "Opening stock price on 2023-06-02?"
    assert "explicit_opposite_price_field" in codes(q, "Closing price was $21.")
    assert "explicit_answer_date_mismatch" in codes(q, "$21 as of 2023-06-03")
    for answer in (
        "$21",
        "Not the closing price: $21",
        "$21 as of 2023-06-02",
        "$21 as of 2023-02-30",
    ):
        assert not codes(q, answer)
    assert not codes("Compare prices on 2023-06-02 and 2023-06-03", "$21 as of 2023-06-03")


def test_missing_fields_are_unresolved_binding_preserves_raw_answer():
    a = diagnose_contract("Who directed the film?", "Example Person", ["source1"])
    assert a["status"] == "unresolved"
    assert (
        a["binding_sha256"]
        != diagnose_contract("Who directed the film?", "Other", ["source1"])["binding_sha256"]
    )
    assert (
        a["binding_sha256"]
        != diagnose_contract("Who directed the film?", "Example Person", ["source2"])[
            "binding_sha256"
        ]
    )
    assert diagnose_contract("Who?", "I don't know.")["status"] == "generator_abstained"
