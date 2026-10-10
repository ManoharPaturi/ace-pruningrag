"""Fresh-process GPU generation under the same isolated versions as retrieval."""

import argparse
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
    import importlib.metadata

    import torch

    from ace_pruningrag.artifacts import read_json, write_json
    from ace_pruningrag.daily_prices import DailyPrices
    from ace_pruningrag.generation import generated_pilot

    expected = {
        "transformers": "4.57.3",
        "huggingface_hub": "0.36.0",
        "tokenizers": "0.22.1",
        "safetensors": "0.6.2",
        "sentencepiece": "0.2.1",
    }
    versions = {name: importlib.metadata.version(name) for name in expected}
    if versions != expected:
        raise ValueError("isolated versions differ from protocol")
    runtime = dict(
        versions,
        torch=torch.__version__,
        cuda=torch.version.cuda,
        gpus=[torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
    )
    prices = DailyPrices(read_json(args.root / "configs/crag_prices.json"), args.root)
    audit = prices.audit()
    write_json(args.output / "price_audit.json", audit)
    result = generated_pilot(
        args.root / "configs/generated_pilot.json",
        args.root,
        args.output / "generated",
        runtime,
        audit,
        prices,
    )
    write_json(
        args.output / "completion.json",
        {
            "status": result["status"],
            "queries": result["queries"],
            "actual_llm_calls": result["actual_llm_calls"],
            "runtime": runtime,
        },
    )


if __name__ == "__main__":
    main()
