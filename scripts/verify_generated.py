"""Independent raw-input, token-budget, output decoding, and exact-agreement verification."""

import argparse
import hashlib
import itertools
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from transformers import AutoTokenizer

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.daily_prices import DailyPrices
from ace_pruningrag.dataset import iter_records, verify_dataset
from ace_pruningrag.evidence import web_chunks
from ace_pruningrag.retrieval import bm25_rank


def verify(root: Path, run: Path) -> dict:
    manifest = read_json(run / "manifest.json")
    config = manifest["config"]
    summary = read_json(run / "summary.json")
    assert sha256_file(run / "predictions.jsonl") == manifest["trace_sha256"]
    tokenizer = AutoTokenizer.from_pretrained(
        root / config["generator"]["directory"], local_files_only=True, trust_remote_code=False
    )
    historical = config["scope"] == "adapted_historical_routing_diagnostic"
    if historical:
        assert config == read_json(root / "configs/historical_routing.json")
        prices = DailyPrices(read_json(root / "configs/crag_prices.json"), root)
    records = {
        r.interaction_id: r
        for r in (
            (
                r
                for r in iter_records(verify_dataset(manifest["dataset"], root))
                if r.interaction_id in config["query_ids"]
            )
            if historical
            else itertools.islice(
                iter_records(verify_dataset(manifest["dataset"], root)), config["limit"]
            )
        )
    }
    assert list(records) == manifest["query_ids"]
    expected_runtime = {
        "transformers": "4.57.3",
        "huggingface_hub": "0.36.0",
        "tokenizers": "0.22.1",
        "safetensors": "0.6.2",
        "sentencepiece": "0.2.1",
    }
    assert all(manifest["runtime"][key] == value for key, value in expected_runtime.items())
    assert manifest["runtime"]["gpus"] and manifest["runtime"]["cuda"]
    assert config["generator"]["dtype"] == "float32"
    assert summary["numerical_diagnostic"] == {
        "dtype": "float32",
        "all_parameters_finite": True,
        "per_step_scores_guarded": True,
    }
    rows = [json.loads(line) for line in (run / "predictions.jsonl").read_text().splitlines()]
    assert len(rows) == len(records) * len(config["policies"])
    assert not all(row["output_ids"] and set(row["output_ids"]) == {0} for row in rows)
    seen = set()
    groups = defaultdict(list)
    for row in rows:
        pair = (row["interaction_id"], row["policy"])
        assert pair not in seen
        seen.add(pair)
        assert row["policy"] in config["policies"]
        record = records[row["interaction_id"]]
        q = record.inference_input()
        assert row["query"] == q.query and row["query_time"] == q.query_time
        pool = bm25_rank(q.query, web_chunks(q, config["chunk_words"]))[: config["candidate_limit"]]
        original = {e.evidence_id: e.as_dict() for e, _ in pool}
        api_used = historical and (
            row["policy"] == "all_available"
            or (
                row["policy"] == "adaptive"
                and re.search(
                    r"\b(?:stock price|share price|best performer|daily moves|price change)\b",
                    q.query,
                    re.I,
                )
                is not None
            )
        )
        expected_candidates = [e.evidence_id for e, _ in pool]
        if api_used:
            api_rows = [e for e in row["selected"] if e["source_kind"] == "api"]
            # The short API row ranks first on relevance and must fit this frozen budget.
            assert len(api_rows) == 1
            e = api_rows[0]
            question_date = datetime.strptime(q.query_time, "%m/%d/%Y, %H:%M:%S PT").date()
            requested = (question_date - timedelta(days=1)).isoformat()
            assert e["requested_date"] == requested < question_date.isoformat()
            assert e["available_as_of"] == question_date.isoformat()
            possessives = {
                t.upper() for t in re.findall(r"\b([A-Za-z][A-Za-z0-9]{2,5})['’]s\b", q.query)
            }
            assert e["ticker"] in possessives
            response = prices.lookup(e["ticker"], requested)
            assert len(response) == 1
            timestamp, values = next(iter(response.items()))
            price_hash = sha256_file(prices.path)
            api = {
                "content": f"{e['ticker']} closing price on {requested}: {values['Close']}",
                "source_ref": f"crag:{price_hash}/finance_price/{e['ticker']}/{timestamp}",
                "ticker": e["ticker"],
                "requested_date": requested,
                "row_timestamp": timestamp,
                "available_as_of": question_date.isoformat(),
                "close": values["Close"],
                "snapshot_sha256": price_hash,
                "limitations": "Currency and adjustment basis are not established by this row.",
            }
            identity = hashlib.sha256(json.dumps(api, sort_keys=True).encode()).hexdigest()
            original[identity] = dict(api, evidence_id=identity, source_kind="api")
            expected_candidates.append(identity)
        assert row["actual_source_calls"] == {"web": 1, "finance": int(bool(api_used))}
        assert row["candidate_ids"] == expected_candidates
        assert row["actual_llm_calls"] == 1
        assert not any(key in row for key in ("answer", "domain", "split", "alt_ans"))
        assert len(row["selected"]) <= config["max_items"]
        assert len({e["evidence_id"] for e in row["selected"]}) == len(row["selected"])
        for e in row["selected"]:
            assert e == original[e["evidence_id"]]
            if e["source_kind"] == "web":
                page = q.search_results[e["page_index"]]
                assert page[e["field"]][e["char_start"] : e["char_end"]] == e["content"]
        context = "\n\n".join(
            f"[{e['evidence_id']}] {e['source_kind']} "
            f"{e.get('source_url') or e.get('source_ref') or 'page:' + str(e['page_index'])}"
            f"\n{e['content']}"
            for e in sorted(row["selected"], key=lambda e: e["evidence_id"])
        )
        msg = [
            {"role": "system", "content": config["system_prompt"]},
            {
                "role": "user",
                "content": (
                    f"Question timestamp: {q.query_time}\nQuestion: {q.query}\n"
                    f"<evidence>\n{context}\n</evidence>\nAnswer:"
                ),
            },
        ]
        assert (
            hashlib.sha256(json.dumps(msg, ensure_ascii=False).encode()).hexdigest()
            == row["prompt_sha256"]
        )
        ids = tokenizer.apply_chat_template(msg, tokenize=True, add_generation_prompt=True)
        assert len(ids) == row["input_tokens"]
        assert len(row["output_ids"]) == row["output_tokens"] <= config["max_new_tokens"]
        assert row["input_tokens"] + row["output_tokens"] <= config["total_tokens"]
        assert row["input_tokens"] + config["max_new_tokens"] <= config["total_tokens"]
        assert (
            tokenizer.decode(row["output_ids"], skip_special_tokens=True).strip()
            == row["prediction"]
        )
        normalized = row["prediction"].strip().casefold()
        exact = any(normalized == answer.strip().casefold() for answer in record.answers)
        abstained = normalized in {
            "i don't know",
            "i don't know.",
            "i do not know",
            "i do not know.",
        }
        outcome = (
            "abstained" if abstained else "exact_agreement" if exact else "needs_semantic_review"
        )
        assert row["evaluation"] == {
            "exact_agreement": exact,
            "abstained": abstained,
            "outcome": outcome,
        }
        assert all(
            math.isfinite(row[key]) and row[key] >= 0
            for key in ("generation_seconds", "retrieval_seconds")
        )
        assert row["plan"]["total_budget"] == config["total_tokens"]
        allocations = dict(row["plan"]["allocations"])
        assert set(allocations) == ({"web", "finance_prices"} if api_used else {"web"})
        assert sum(allocations.values()) == row["plan"]["evidence_budget"]
        budget = row["plan"]["evidence_budget"]
        assert allocations == (
            {"finance_prices": (budget + 1) // 2, "web": budget // 2}
            if api_used
            else {"web": budget}
        )
        empty_msg = [
            msg[0],
            {
                "role": "user",
                "content": (
                    f"Question timestamp: {q.query_time}\nQuestion: {q.query}\n"
                    "<evidence>\n\n</evidence>\nAnswer:"
                ),
            },
        ]
        empty_count = len(
            tokenizer.apply_chat_template(empty_msg, tokenize=True, add_generation_prompt=True)
        )
        assert row["plan"]["reserved_tokens"] == empty_count + config["max_new_tokens"]
        for source, kind in (("web", "web"), ("finance_prices", "api")):
            subset = [e for e in row["selected"] if e["source_kind"] == kind]
            parts = []
            for e in sorted(subset, key=lambda e: e["evidence_id"]):
                ref = (
                    (e["source_url"] or "page:" + str(e["page_index"]))
                    if kind == "web"
                    else e["source_ref"]
                )
                parts.append(f"[{e['evidence_id']}] {kind} {ref}\n{e['content']}")
            subcontext = "\n\n".join(parts)
            submsg = [
                msg[0],
                {
                    "role": "user",
                    "content": (
                        f"Question timestamp: {q.query_time}\nQuestion: {q.query}\n"
                        f"<evidence>\n{subcontext}\n</evidence>\nAnswer:"
                    ),
                },
            ]
            count = len(
                tokenizer.apply_chat_template(submsg, tokenize=True, add_generation_prompt=True)
            )
            assert max(0, count - empty_count) <= allocations.get(source, 0)
        assert (
            row["plan"]["evidence_budget"] + row["plan"]["reserved_tokens"]
            == config["total_tokens"]
        )
        groups[row["policy"]].append(row)
    for policy, group in groups.items():
        reported = summary["policies"][policy]
        assert len(group) == config["limit"]
        assert reported["outcomes"] == dict(Counter(r["evaluation"]["outcome"] for r in group))
        assert reported["exact_agreement_rate"] == sum(
            r["evaluation"]["exact_agreement"] for r in group
        ) / len(group)
        assert reported["abstention_rate"] == sum(
            r["evaluation"]["abstained"] for r in group
        ) / len(group)
        for field in ("input_tokens", "output_tokens", "generation_seconds", "retrieval_seconds"):
            assert math.isclose(reported["mean_" + field], statistics.mean(r[field] for r in group))
        assert reported["maximum_total_tokens"] == max(
            r["input_tokens"] + r["output_tokens"] for r in group
        )
        assert reported["semantic_accuracy"] is None and reported["unsupported_claim_rate"] is None
    assert summary["actual_llm_calls"] == len(rows)
    assert summary["actual_web_retrieval_calls"] == len(rows) and summary[
        "actual_finance_calls"
    ] == sum(r["actual_source_calls"]["finance"] for r in rows)
    assert summary["published_baseline_reproduced"] is False
    return {
        "status": "independently_verified",
        "queries": len(records),
        "generated_answers": len(rows),
        "actual_llm_calls": len(rows),
        "maximum_reserved_tokens": max(r["input_tokens"] + config["max_new_tokens"] for r in rows),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(args.root, args.run)
    if args.output:
        write_json(args.output, result)
    print(json.dumps(result, indent=2))
