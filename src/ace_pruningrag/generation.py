"""Pinned adapted generator pilot with real prompt-token budgets and separate scoring."""

import hashlib
import json
import statistics
import time
from collections import Counter
from itertools import islice
from pathlib import Path

from .artifacts import read_json, sha256_file, write_json
from .dataset import QueryInput, iter_records, verify_dataset
from .evidence import web_chunks
from .retrieval import bm25_rank
from .routing import Capability, route
from .selection import Candidate, SelectionProblem, render_context


def messages(query: QueryInput, selected: tuple[Candidate, ...], system_prompt: str) -> list[dict]:
    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Question timestamp: {query.query_time}\nQuestion: {query.query}\n"
            f"<evidence>\n{render_context(selected)}\n</evidence>\nAnswer:",
        },
    ]


def evaluate_answer(prediction: str, answers: tuple[str, ...]) -> dict:
    normalized = prediction.strip().casefold()
    exact = normalized in {answer.strip().casefold() for answer in answers}
    abstained = normalized in {"i don't know", "i don't know.", "i do not know", "i do not know."}
    return {
        "exact_agreement": exact,
        "abstained": abstained,
        "outcome": "abstained"
        if abstained
        else "exact_agreement"
        if exact
        else "needs_semantic_review",
    }


def prepare_context(query, config, policy, tokenize, capabilities, api_fetch=None):
    empty_tokens = len(tokenize(messages(query, (), config["system_prompt"])))
    reserve = empty_tokens + config["max_new_tokens"]
    plan = route(query, capabilities, policy, config["total_tokens"], reserve)
    start = time.perf_counter()
    allocations = dict(plan.allocations)
    ranked = (
        bm25_rank(query.query, web_chunks(query, config["chunk_words"]))[
            : config["candidate_limit"]
        ]
        if "web" in allocations
        else []
    )
    maximum = max((score for _, score in ranked), default=0) or 1
    candidates = [
        Candidate(
            item.evidence_id,
            item.content,
            "web",
            item.source_url or f"page:{item.page_index}",
            score / maximum,
            (0.0,),
        )
        for item, score in ranked
    ]
    evidence = {item.evidence_id: item.as_dict() for item, _ in ranked}
    source_calls = {"web": int("web" in allocations), "finance": 0}
    if "finance_prices" in allocations:
        if api_fetch is None:
            raise ValueError("finance allocation has no executor")
        api = api_fetch()
        source_calls["finance"] += 1
        identity = hashlib.sha256(json.dumps(api, sort_keys=True).encode()).hexdigest()
        item = Candidate(identity, api["content"], "api", api["source_ref"], 1.0, (0.0,))
        candidates.append(item)
        evidence[identity] = dict(api, evidence_id=identity, source_kind="api")

    def cost(items):
        for source, kind in (("web", "web"), ("finance_prices", "api")):
            group = tuple(item for item in items if item.source_kind == kind)
            source_cost = max(
                0, len(tokenize(messages(query, group, config["system_prompt"]))) - empty_tokens
            )
            if source_cost > allocations.get(source, 0):
                return config["total_tokens"] + 1
        return (
            len(tokenize(messages(query, items, config["system_prompt"])))
            + config["max_new_tokens"]
        )

    problem = SelectionProblem(
        candidates,
        ("unused_by_top_k",),
        (),
        {},
        {},
        cost,
        config["total_tokens"],
        config["max_items"],
    )
    selected = problem.select("top_k") if plan.allocations else ()
    input_ids = tokenize(messages(query, selected, config["system_prompt"]))
    if len(input_ids) + config["max_new_tokens"] > config["total_tokens"]:
        raise ValueError("complete model request exceeds matched total-token budget")
    return {
        "plan": plan.as_dict(),
        "selected": selected,
        "messages": messages(query, selected, config["system_prompt"]),
        "input_ids": input_ids,
        "evidence": [evidence[item.evidence_id] for item in selected],
        "candidate_ids": [item.evidence_id for item in candidates],
        "source_calls": source_calls,
        "retrieval_seconds": time.perf_counter() - start,
    }


def generated_pilot(
    config_path: Path, root: Path, output: Path, runtime: dict, price_audit: dict, prices
) -> dict:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, LogitsProcessor

    config = read_json(config_path)
    if config["scope"] != "adapted_phase3_generated_answer_pilot" or config["limit"] != 50:
        raise ValueError("only frozen 50-question adapted pilot allowed")
    if (
        config["policies"] != ["fixed_web", "all_available", "adaptive"]
        or config["sampling"] is not False
    ):
        raise ValueError("fixed deterministic policy contract required")
    if not torch.cuda.is_available():
        raise ValueError("real GPU execution required")
    torch.manual_seed(config["seed"])
    torch.cuda.manual_seed_all(config["seed"])
    torch.backends.cudnn.benchmark = False
    model_dir = root / config["generator"]["directory"]
    loading_start = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(
        model_dir, local_files_only=True, trust_remote_code=False
    )
    if config["generator"]["dtype"] != "float32":
        raise ValueError("generated pilot requires numerically checked float32")
    model = (
        AutoModelForCausalLM.from_pretrained(
            model_dir,
            local_files_only=True,
            trust_remote_code=False,
            torch_dtype=torch.float32,
            attn_implementation="eager",
        )
        .to("cuda:0")
        .eval()
    )
    parameters_finite = all(bool(torch.isfinite(p).all().item()) for p in model.parameters())
    if not parameters_finite:
        raise ValueError("nonfinite model parameters")

    class FiniteScores(LogitsProcessor):
        def __call__(self, input_ids, scores):
            if (
                torch.isnan(scores).any()
                or torch.isposinf(scores).any()
                or not torch.isfinite(scores).any(dim=-1).all()
            ):
                raise ValueError("nonfinite or entirely masked generation scores")
            return scores

    numerical_diagnostic = {
        "dtype": "float32",
        "all_parameters_finite": parameters_finite,
        "per_step_scores_guarded": True,
    }
    loading_seconds = time.perf_counter() - loading_start

    def tokenize(msg):
        return tokenizer.apply_chat_template(msg, tokenize=True, add_generation_prompt=True)

    # Finance prices are date-bearing, but preflight probes must actually cover the sample.
    last_date = price_audit["probes"]["AAPL"]["last_date"]
    preflight_calls = 0
    dataset_config = read_json(root / config["dataset_config"])
    dataset = verify_dataset(dataset_config, root)
    output.mkdir(parents=True, exist_ok=False)
    ids = []
    rows = []
    with (output / "predictions.jsonl").open("x", encoding="utf-8") as stream:
        for index, record in enumerate(islice(iter_records(dataset), config["limit"])):
            query = record.inference_input()
            ids.append(query.interaction_id)
            import re
            from datetime import datetime

            aliases = {"apple": "AAPL", "microsoft": "MSFT", "tesla": "TSLA"}
            symbols = {
                ticker
                for name, ticker in aliases.items()
                if re.search(r"\b" + name + r"\b", query.query, re.I)
            }
            symbols.update(
                ticker
                for ticker in aliases.values()
                if re.search(r"\b" + ticker + r"\b", query.query, re.I)
            )
            date = datetime.strptime(query.query_time, "%m/%d/%Y, %H:%M:%S PT").date().isoformat()
            ticker = next(iter(symbols)) if len(symbols) == 1 else None
            price_available = False
            if ticker:
                preflight_calls += 1
                price_available = prices.lookup(ticker, date) is not None
            capabilities = (
                Capability("web", True, False, None),
                Capability("finance_market_cap", True, True, None),
                Capability("finance_ticker", True, True, None),
                Capability(
                    "finance_prices", price_available, True, date if price_available else last_date
                ),
            )

            def api_fetch(ticker=ticker, date=date):
                response = prices.lookup(ticker, date)
                if response is None:
                    raise ValueError("dated price disappeared after preflight")
                return {
                    "content": f"Historical daily prices for {ticker} on {date}: "
                    + json.dumps(response, sort_keys=True),
                    "source_ref": (
                        f"crag:{price_audit['asset_sha256']}/finance_price/{ticker}/{date}"
                    ),
                    "ticker": ticker,
                    "date": date,
                    "response": response,
                    "snapshot_sha256": price_audit["asset_sha256"],
                }

            # Rotate which policy runs first to reduce systematic warm-up/order bias.
            order = config["policies"][index % 3 :] + config["policies"][: index % 3]
            for policy in order:
                prepared = prepare_context(query, config, policy, tokenize, capabilities, api_fetch)
                inputs = torch.tensor([prepared["input_ids"]], device="cuda:0")
                torch.cuda.synchronize()
                started = time.perf_counter()
                with torch.inference_mode():
                    generated = model.generate(
                        input_ids=inputs,
                        attention_mask=torch.ones_like(inputs),
                        logits_processor=[FiniteScores()],
                        do_sample=False,
                        num_beams=1,
                        max_new_tokens=config["max_new_tokens"],
                        pad_token_id=tokenizer.eos_token_id,
                        temperature=None,
                        top_p=None,
                        top_k=None,
                    )
                torch.cuda.synchronize()
                seconds = time.perf_counter() - started
                tail = generated[0, inputs.shape[1] :].tolist()
                prediction = tokenizer.decode(tail, skip_special_tokens=True).strip()
                prompt_tokens = len(prepared["input_ids"])
                if prompt_tokens + len(tail) > config["total_tokens"]:
                    raise ValueError("executed token cap exceeded")
                result = {
                    "interaction_id": query.interaction_id,
                    "query": query.query,
                    "query_time": query.query_time,
                    "policy": policy,
                    "execution_order": order,
                    "plan": prepared["plan"],
                    "candidate_ids": prepared["candidate_ids"],
                    "selected": prepared["evidence"],
                    "prompt_sha256": hashlib.sha256(
                        json.dumps(prepared["messages"], ensure_ascii=False).encode()
                    ).hexdigest(),
                    "input_tokens": prompt_tokens,
                    "output_tokens": len(tail),
                    "output_ids": tail,
                    "prediction": prediction,
                    "generation_seconds": seconds,
                    "retrieval_seconds": prepared["retrieval_seconds"],
                    "actual_source_calls": prepared["source_calls"],
                    "actual_llm_calls": 1,
                    "evaluation": evaluate_answer(prediction, record.answers),
                }
                rows.append(result)
                stream.write(json.dumps(result, ensure_ascii=False) + "\n")
                stream.flush()
            print(f"Generated query {index + 1}/{config['limit']}, all three policies", flush=True)
    summary = {
        "status": "adapted_generated_pilot_completed",
        "queries": len(ids),
        "actual_llm_calls": len(rows),
        "actual_web_retrieval_calls": sum(r["actual_source_calls"]["web"] for r in rows),
        "actual_finance_calls": sum(r["actual_source_calls"]["finance"] for r in rows),
        "price_preflight_calls": preflight_calls,
        "generator": config["generator"],
        "policies": {},
        "model_loading_seconds": loading_seconds,
        "numerical_diagnostic": numerical_diagnostic,
        "runtime": runtime,
        "full_scientific_phase3_complete": False,
        "published_baseline_reproduced": False,
        "limitations": [
            "Adapted generator and price executor; not original PruningRAG reproduction.",
            "First 50 file-order development questions, no held-out publication benchmark.",
            "Non-exact answers require independent semantic and grounding review.",
            "Price availability requires actual matching rows; no invented data.",
        ],
    }
    for policy in config["policies"]:
        group = [r for r in rows if r["policy"] == policy]
        outcomes = Counter(r["evaluation"]["outcome"] for r in group)
        summary["policies"][policy] = {
            "queries": len(group),
            "outcomes": dict(outcomes),
            "exact_agreement_rate": sum(r["evaluation"]["exact_agreement"] for r in group)
            / len(group),
            "abstention_rate": sum(r["evaluation"]["abstained"] for r in group) / len(group),
            "mean_input_tokens": statistics.mean(r["input_tokens"] for r in group),
            "mean_output_tokens": statistics.mean(r["output_tokens"] for r in group),
            "maximum_total_tokens": max(r["input_tokens"] + r["output_tokens"] for r in group),
            "mean_generation_seconds": statistics.mean(r["generation_seconds"] for r in group),
            "mean_retrieval_seconds": statistics.mean(r["retrieval_seconds"] for r in group),
            "semantic_accuracy": None,
            "unsupported_claim_rate": None,
        }
    triples = [[r for r in rows if r["interaction_id"] == identity] for identity in ids]
    summary["identical_prompts_across_policies"] = sum(
        len({r["prompt_sha256"] for r in group}) == 1 for group in triples
    )
    summary["identical_predictions_across_policies"] = sum(
        len({r["prediction"] for r in group}) == 1 for group in triples
    )
    write_json(output / "summary.json", summary)
    write_json(
        output / "manifest.json",
        {
            "config": config,
            "config_sha256": sha256_file(config_path),
            "dataset": dataset_config,
            "price_audit": price_audit,
            "query_ids": ids,
            "runtime": runtime,
            "trace_sha256": sha256_file(output / "predictions.jsonl"),
            "source_sha256": {
                str(p.relative_to(root)): sha256_file(p)
                for p in sorted((root / "src/ace_pruningrag").glob("*.py"))
            },
        },
    )
    return summary
