"""One bounded fresh generation after a missing dated-price evidence round."""

import hashlib
import json
import time
from collections import Counter, defaultdict

from .artifacts import read_json, sha256_file, write_json
from .generation import prepare_context
from .historical_comparison import historical_source
from .historical_prices import prior_close_request
from .reliability import PriceClaim, sufficient, verify_price_answer


def selected_claims(evidence):
    return tuple(
        PriceClaim(e["ticker"], e["requested_date"], e["close"], e["source_ref"])
        for e in evidence
        if e["source_kind"] == "api"
    )


def retry_needed(request, evidence):
    return not sufficient(request, selected_claims(evidence))


def regenerate(root, output, rows, queries, model, tokenizer, guard, prices, snapshot):
    import torch

    protocol = read_json(root / "configs/bounded_regeneration.json")
    expected = {
        "scope": "historical_development_bounded_regeneration",
        "baseline_config": "configs/historical_routing.json",
        "max_extra_rounds": 1,
        "max_total_llm_calls": 26,
        "per_round_total_tokens": 2048,
        "per_request_total_reserved_tokens_cap": 4096,
        "trigger": "missing_sufficient_structured_dated_price",
        "retry_policy": "all_available",
        "regenerate_existing_abstentions_with_missing_evidence": True,
        "publication_results": False,
    }
    if protocol != expected:
        raise ValueError("only frozen bounded regeneration protocol allowed")
    config = read_json(root / protocol["baseline_config"])
    retries, decisions = [], []
    validation_reads = 0

    def tokenize(msg):
        return tokenizer.apply_chat_template(msg, tokenize=True, add_generation_prompt=True)

    for row in rows:
        q = queries[row["interaction_id"]]
        request = prior_close_request(q, _inventory(prices))
        if request is None:
            raise ValueError("historical request invalid")
        original_claims = selected_claims(row["selected"])
        before = verify_price_answer(row["prediction"], request, original_claims)
        after = before
        final_prediction = row["prediction"]
        if retry_needed(request, row["selected"]):
            if len(rows) + len(retries) >= protocol["max_total_llm_calls"]:
                raise ValueError("stop before exceeding total model-call cap")
            caps, fetch = historical_source(q, prices, snapshot)
            validation_reads += 1
            prepared = prepare_context(q, config, "all_available", tokenize, caps, fetch)
            if retry_needed(request, prepared["evidence"]):
                raise ValueError("retry failed to supply dated price; stop without generation")
            inputs = torch.tensor([prepared["input_ids"]], device="cuda:0")
            torch.cuda.synchronize()
            start = time.perf_counter()
            with torch.inference_mode():
                result = model.generate(
                    input_ids=inputs,
                    attention_mask=torch.ones_like(inputs),
                    logits_processor=[guard],
                    do_sample=False,
                    num_beams=1,
                    max_new_tokens=config["max_new_tokens"],
                    pad_token_id=tokenizer.eos_token_id,
                    temperature=None,
                    top_p=None,
                    top_k=None,
                )
            torch.cuda.synchronize()
            tail = result[0, inputs.shape[1] :].tolist()
            final_prediction = tokenizer.decode(tail, skip_special_tokens=True).strip()
            reserved = len(prepared["input_ids"]) + config["max_new_tokens"]
            combined = row["input_tokens"] + config["max_new_tokens"] + reserved
            if reserved > 2048 or combined > 4096 or len(tail) > config["max_new_tokens"]:
                raise ValueError("per-round or cumulative token cap exceeded")
            after = verify_price_answer(
                final_prediction, request, selected_claims(prepared["evidence"])
            )
            retries.append(
                {
                    "interaction_id": q.interaction_id,
                    "policy": row["policy"],
                    "retry_policy": "all_available",
                    "query": q.query,
                    "query_time": q.query_time,
                    "selected": prepared["evidence"],
                    "plan": prepared["plan"],
                    "candidate_ids": prepared["candidate_ids"],
                    "prompt_sha256": hashlib.sha256(
                        json.dumps(prepared["messages"], ensure_ascii=False).encode()
                    ).hexdigest(),
                    "input_tokens": len(prepared["input_ids"]),
                    "output_tokens": len(tail),
                    "output_ids": tail,
                    "prediction": final_prediction,
                    "combined_reserved_tokens": combined,
                    "generation_seconds": time.perf_counter() - start,
                    "retrieval_seconds": prepared["retrieval_seconds"],
                    "actual_source_calls": prepared["source_calls"],
                    "actual_llm_calls": 1,
                }
            )
        decisions.append(
            {
                "interaction_id": q.interaction_id,
                "policy": row["policy"],
                "before_verdict": before,
                "after_verdict": after,
                "retried": retry_needed(request, row["selected"]),
                "final_prediction": final_prediction,
                "released_answer": final_prediction
                if after == "supported_price_field"
                else "I don't know.",
            }
        )
    if len(rows) + len(retries) > protocol["max_total_llm_calls"]:
        raise ValueError("total model-call cap exceeded")
    output.mkdir(parents=True, exist_ok=False)
    for name, items in (("predictions", retries), ("decisions", decisions)):
        (output / f"{name}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in items))
    groups = defaultdict(list)
    for row in decisions:
        groups[row["policy"]].append(row)
    summary = {
        "status": "bounded_regeneration_completed",
        "protocol": protocol,
        "initial_llm_calls": len(rows),
        "extra_llm_calls": len(retries),
        "total_llm_calls": len(rows) + len(retries),
        "actual_judge_calls": 0,
        "extra_web_calls": sum(r["actual_source_calls"]["web"] for r in retries),
        "extra_finance_calls": sum(r["actual_source_calls"]["finance"] for r in retries),
        "extra_validation_price_reads": validation_reads,
        "inventory_reads": len(rows) + validation_reads,
        "total_input_tokens": sum(r["input_tokens"] for r in rows + retries),
        "total_output_tokens": sum(r["output_tokens"] for r in rows + retries),
        "maximum_combined_reserved_tokens": max(
            (r["combined_reserved_tokens"] for r in retries), default=0
        ),
        "extra_generation_seconds": sum(r["generation_seconds"] for r in retries),
        "per_policy": {
            p: {
                "requests": len(items),
                "retries": sum(r["retried"] for r in items),
                "before_verdicts": dict(Counter(r["before_verdict"] for r in items)),
                "after_verdicts": dict(Counter(r["after_verdict"] for r in items)),
            }
            for p, items in groups.items()
        },
        "human_semantic_accuracy": None,
        "held_out_evaluation": False,
        "full_phase4_research_gate_passed": False,
    }
    write_json(output / "summary.json", summary)
    write_json(
        output / "manifest.json",
        {
            "protocol_sha256": sha256_file(root / "configs/bounded_regeneration.json"),
            "initial_trace_sha256": sha256_file(output.parent / "generated/predictions.jsonl"),
            "trace_sha256": sha256_file(output / "predictions.jsonl"),
            "decisions_sha256": sha256_file(output / "decisions.jsonl"),
            "snapshot_sha256": snapshot,
        },
    )
    return summary


def _inventory(prices):
    import sqlite3
    from urllib.parse import quote

    with sqlite3.connect(f"file:{quote(str(prices.path.resolve()))}?mode=ro", uri=True) as db:
        return {row[0] for row in db.execute('SELECT key FROM "unnamed"')}
