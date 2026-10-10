"""Actual pinned-tokenizer CPU preparation; no generator weights or model calls."""

import argparse
import json
from itertools import islice
from pathlib import Path

from transformers import AutoTokenizer

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.assets import fetch_assets
from ace_pruningrag.dataset import iter_records, verify_dataset
from ace_pruningrag.generation import prepare_context
from ace_pruningrag.routing import Capability


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path.cwd()
    config = read_json(root / "configs/generated_pilot.json")
    small = dict(
        config,
        assets=[a for a in config["assets"] if not a["local_path"].endswith(".safetensors")],
        max_total_bytes=20000000,
    )
    fetch_assets(small, root)
    tokenizer = AutoTokenizer.from_pretrained(
        root / config["generator"]["directory"], local_files_only=True, trust_remote_code=False
    )

    def tokenize(msg):
        return tokenizer.apply_chat_template(msg, tokenize=True, add_generation_prompt=True)

    dataset = verify_dataset(read_json(root / config["dataset_config"]), root)
    args.output.mkdir(parents=True, exist_ok=False)
    count = 0
    maximum = 0
    caps = (
        Capability("web", True, False, None),
        Capability("finance_prices", False, True, "2024-02-28"),
        Capability("finance_market_cap", True, True, None),
        Capability("finance_ticker", True, True, None),
    )
    with (args.output / "prepared.jsonl").open("x") as stream:
        for record in islice(iter_records(dataset), config["limit"]):
            q = record.inference_input()
            for policy in config["policies"]:
                prepared = prepare_context(q, config, policy, tokenize, caps)
                total = len(prepared["input_ids"]) + config["max_new_tokens"]
                assert total <= config["total_tokens"]
                maximum = max(maximum, total)
                count += 1
                stream.write(
                    json.dumps(
                        {
                            "interaction_id": q.interaction_id,
                            "policy": policy,
                            "reserved_request_tokens": total,
                            "selected_ids": [e["evidence_id"] for e in prepared["evidence"]],
                            "actual_llm_calls": 0,
                        }
                    )
                    + "\n"
                )
    result = {
        "status": "real_tokenizer_preflight_completed",
        "requests": count,
        "maximum_reserved_request_tokens": maximum,
        "actual_llm_calls": 0,
        "config_sha256": sha256_file(root / "configs/generated_pilot.json"),
    }
    write_json(args.output / "summary.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
