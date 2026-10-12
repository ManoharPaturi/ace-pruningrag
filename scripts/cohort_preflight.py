"""Prepare all 250 prospective selector requests with the actual model tokenizer."""

import argparse
from pathlib import Path

from transformers import AutoTokenizer

from ace_pruningrag.artifacts import write_json
from ace_pruningrag.assets import fetch_assets
from ace_pruningrag.cohort import load_cohort, prepare_selectors

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path.cwd()
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    protocol, config, records = load_cohort(root, args.output / "cohort")
    fetch_assets(
        dict(
            config,
            assets=[a for a in config["assets"] if not a["local_path"].endswith(".safetensors")],
            max_total_bytes=20000000,
        ),
        root,
    )
    tokenizer = AutoTokenizer.from_pretrained(
        root / config["generator"]["directory"], local_files_only=True, trust_remote_code=False
    )
    counts, maximum = 0, 0
    for index, record in enumerate(records):
        prepared, _ = prepare_selectors(
            record.inference_input(),
            config,
            lambda msg: tokenizer.apply_chat_template(
                msg, tokenize=True, add_generation_prompt=True
            ),
        )
        for request in prepared.values():
            counts += 1
            maximum = max(maximum, len(request["input_ids"]) + config["max_new_tokens"])
        print(f"Prepared {index + 1}/50", flush=True)
    assert counts == protocol["max_llm_calls"]
    write_json(
        args.output / "summary.json",
        {
            "status": "cohort_preflight_completed",
            "queries": 50,
            "requests": counts,
            "maximum_reserved_tokens": maximum,
            "actual_llm_calls": 0,
            "packet_sha256": protocol["packet_sha256"],
        },
    )
