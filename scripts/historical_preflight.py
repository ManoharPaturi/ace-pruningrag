"""Real dated source and full model-tokenizer preparation of all 18 frozen requests."""

import argparse
import json
from pathlib import Path

from transformers import AutoTokenizer

from ace_pruningrag.artifacts import read_json, write_json
from ace_pruningrag.assets import fetch_assets
from ace_pruningrag.daily_prices import DailyPrices
from ace_pruningrag.dataset import iter_records, verify_dataset
from ace_pruningrag.generation import prepare_context
from ace_pruningrag.historical_comparison import historical_source

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--retry", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    config = read_json(root / "configs/historical_routing.json")
    fetch_assets(
        dict(
            config,
            assets=[a for a in config["assets"] if not a["local_path"].endswith(".safetensors")],
            max_total_bytes=20000000,
        ),
        root,
    )
    prices = DailyPrices(read_json(root / "configs/crag_prices.json"), root)
    audit = prices.audit()
    tokenizer = AutoTokenizer.from_pretrained(
        root / config["generator"]["directory"], local_files_only=True, trust_remote_code=False
    )

    def tokenize(msg):
        return tokenizer.apply_chat_template(msg, tokenize=True, add_generation_prompt=True)

    rows = []
    queries = {}
    for r in iter_records(verify_dataset(read_json(root / config["dataset_config"]), root)):
        if r.interaction_id not in config["query_ids"]:
            continue
        q = r.inference_input()
        queries[q.interaction_id] = q
        caps, fetch = historical_source(q, prices, audit["asset_sha256"])
        for policy in config["policies"]:
            prepared = prepare_context(q, config, policy, tokenize, caps, fetch)
            assert len(prepared["input_ids"]) + config["max_new_tokens"] <= config["total_tokens"]
            rows.append(
                {
                    "interaction_id": q.interaction_id,
                    "policy": policy,
                    "reserved_tokens": len(prepared["input_ids"]) + config["max_new_tokens"],
                    "source_calls": prepared["source_calls"],
                    "selected": prepared["evidence"],
                }
            )
    retries = []
    if args.retry:
        from ace_pruningrag.historical_prices import prior_close_request
        from ace_pruningrag.regeneration import _inventory, retry_needed

        inventory = _inventory(prices)
        for row in rows:
            q = queries[row["interaction_id"]]
            request = prior_close_request(q, inventory)
            if not retry_needed(request, row["selected"]):
                continue
            caps, fetch = historical_source(q, prices, audit["asset_sha256"])
            prepared = prepare_context(q, config, "all_available", tokenize, caps, fetch)
            reserved = len(prepared["input_ids"]) + config["max_new_tokens"]
            assert reserved <= 2048
            assert row["reserved_tokens"] + reserved <= 4096
            assert not retry_needed(request, prepared["evidence"])
            retries.append(
                {
                    "interaction_id": q.interaction_id,
                    "policy": row["policy"],
                    "combined_reserved_tokens": row["reserved_tokens"] + reserved,
                    "source_calls": prepared["source_calls"],
                }
            )
        assert len(retries) == 8
    assert len(rows) == 18
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "prepared.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    if args.retry:
        write_json(args.output / "retry_preparation.json", retries)
    write_json(
        args.output / "summary.json",
        {
            "status": "historical_preflight_completed",
            "requests": len(rows),
            "maximum_reserved_tokens": max(r["reserved_tokens"] for r in rows),
            "actual_llm_calls": 0,
            "retry_requests_prepared": len(retries),
            "finance_calls": sum(r["source_calls"]["finance"] for r in rows),
        },
    )
    print((args.output / "summary.json").read_text())
