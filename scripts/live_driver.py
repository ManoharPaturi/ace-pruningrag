"""Isolated one-question GPU worker; request carries identity only, never answers/labels."""

import argparse
import importlib.metadata
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.overlay))
    sys.path.insert(0, str(args.root / "src"))
    os.environ["USE_TF"] = "0"
    os.environ["USE_FLAX"] = "0"
    from ace_pruningrag.artifacts import read_json, sha256_file, write_json
    from ace_pruningrag.dataset import iter_records, verify_dataset
    from ace_pruningrag.live_generation import generate_one

    expected = {
        "transformers": "4.57.3",
        "huggingface_hub": "0.36.0",
        "tokenizers": "0.22.1",
        "safetensors": "0.6.2",
        "sentencepiece": "0.2.1",
    }
    if {name: importlib.metadata.version(name) for name in expected} != expected:
        raise ValueError("live isolated dependency versions differ")
    request = read_json(args.root / "configs/live_request.json")
    if set(request) != {"interaction_id", "request_id"}:
        raise ValueError("live request accepts identity only")
    config = read_json(args.root / "configs/generated_pilot.json")
    dataset = verify_dataset(read_json(args.root / config["dataset_config"]), args.root)
    query = next(
        (
            r.inference_input()
            for r in iter_records(dataset)
            if r.interaction_id == request["interaction_id"]
        ),
        None,
    )
    if query is None:
        raise ValueError("live request references an unknown pinned question")
    result = generate_one(query, config, args.root)
    result["request_id"] = request["request_id"]
    result["generator"] = config["generator"]
    result["dataset_sha256"] = sha256_file(dataset)
    result["generator_config_sha256"] = sha256_file(args.root / "configs/generated_pilot.json")
    result["dependency_versions"] = expected
    write_json(args.output / "result.json", result)
    write_json(
        args.output / "completion.json",
        {
            "status": "one_live_answer_generated",
            "request_id": request["request_id"],
            "actual_llm_calls": 1,
            "result_sha256": sha256_file(args.output / "result.json"),
        },
    )


if __name__ == "__main__":
    main()
