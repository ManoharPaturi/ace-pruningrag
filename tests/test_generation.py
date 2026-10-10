import io
import pickle

import pytest

from ace_pruningrag.daily_prices import decode_prices
from ace_pruningrag.dataset import QueryInput, validate_record
from ace_pruningrag.generation import evaluate_answer, prepare_context
from ace_pruningrag.routing import Capability


def config():
    return {
        "system_prompt": "Use evidence only.",
        "max_new_tokens": 32,
        "total_tokens": 512,
        "chunk_words": 10,
        "candidate_limit": 12,
        "max_items": 5,
    }


def tokenize(messages):
    # Byte-level toy tokenizer solely for budget arithmetic tests; never a research tokenizer.
    return list((" ".join(m["role"] + " " + m["content"] for m in messages)).encode())


def test_complete_request_budget_and_no_gold_in_messages(row):
    row["query_time"] = "03/05/2024, 23:18:31 PT"
    row["answer"] = "private-gold-sentinel"
    q = validate_record(row).inference_input()
    result = prepare_context(
        q, config(), "adaptive", tokenize, (Capability("web", True, False, None),)
    )
    assert len(result["input_ids"]) + config()["max_new_tokens"] <= config()["total_tokens"]
    assert "private-gold-sentinel" not in str(result["messages"])
    assert result["source_calls"] == {"web": 1, "finance": 0}


def test_fixed_available_adaptive_use_same_generator_contract(row):
    row["query_time"] = "03/05/2024, 23:18:31 PT"
    q = validate_record(row).inference_input()
    caps = (
        Capability("web", True, False, None),
        Capability("finance_prices", False, True, "2024-02-28"),
    )
    prompts = [
        prepare_context(q, config(), p, tokenize, caps)["messages"]
        for p in ("fixed_web", "all_available", "adaptive")
    ]
    assert prompts[0] == prompts[1] == prompts[2]


def test_nonweb_executor_counts_actual_call_and_uses_source_budget():
    q = QueryInput("fixture", "AAPL stock price", "03/05/2024, 23:18:31 PT", ())
    caps = (
        Capability("web", True, False, None),
        Capability("finance_prices", True, True, "2024-03-05"),
    )
    called = []

    def api():
        called.append(True)
        return {"content": "AAPL Close 100.0", "source_ref": "fixture-snapshot/AAPL/2024-03-05"}

    result = prepare_context(q, config(), "adaptive", tokenize, caps, api)
    assert len(called) == 1 and result["source_calls"]["finance"] == 1
    assert any(e["source_kind"] == "api" for e in result["evidence"])
    assert sum(t for _, t in result["plan"]["allocations"]) == result["plan"]["evidence_budget"]


def test_overhead_alone_exceeding_budget_fails():
    q = QueryInput("fixture", "x" * 1000, "03/05/2024, 23:18:31 PT", ())
    with pytest.raises(ValueError):
        prepare_context(q, config(), "fixed_web", tokenize, (Capability("web", True, False, None),))


def test_nonexact_not_silently_graded_incorrect_and_abstentions_separate():
    assert evaluate_answer(" Oracle ", ("oracle",))["outcome"] == "exact_agreement"
    assert evaluate_answer("Oracle Corporation", ("oracle",))["outcome"] == "needs_semantic_review"
    unknown = evaluate_answer("I don't know", ("I don't know",))
    assert unknown["exact_agreement"] is True and unknown["outcome"] == "abstained"


def test_safe_dated_price_container_and_unknown_data_rejected():
    valid = {"2024-02-28 00:00:00 EST": {"Open": 100.0, "Close": 101.0, "Volume": 10}}
    assert decode_prices(pickle.dumps(valid)) == valid
    for value in (
        {"unknown": {"Open": 1, "Close": 2}},
        {"2024-02-28 00:00:00 EST": {"Open": float("nan"), "Close": 1}},
        1,
    ):
        with pytest.raises(ValueError):
            decode_prices(pickle.dumps(value))
    # A global class reference is rejected without instantiating it.
    with pytest.raises(ValueError):
        decode_prices(pickle.dumps(io.BytesIO()))
