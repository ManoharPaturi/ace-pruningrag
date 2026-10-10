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
    for r in iter_records(verify_dataset(read_json(root / config["dataset_config"]), root)):
        if r.interaction_id not in config["query_ids"]:
            continue
        q = r.inference_input()
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
    assert len(rows) == 18
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "prepared.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    write_json(
        args.output / "summary.json",
        {
            "status": "historical_preflight_completed",
            "requests": len(rows),
            "maximum_reserved_tokens": max(r["reserved_tokens"] for r in rows),
            "actual_llm_calls": 0,
            "finance_calls": sum(r["source_calls"]["finance"] for r in rows),
        },
    )
    print((args.output / "summary.json").read_text())
