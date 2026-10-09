"""Fresh-process inference with explicitly isolated library versions."""

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
    import huggingface_hub
    import safetensors
    import sentencepiece
    import tokenizers
    import torch
    import transformers

    from ace_pruningrag.artifacts import read_json, write_json
    from ace_pruningrag.learned_retrieval import learned_smoke

    versions = {
        "transformers": transformers.__version__,
        "huggingface_hub": huggingface_hub.__version__,
        "safetensors": safetensors.__version__,
        "tokenizers": tokenizers.__version__,
        "sentencepiece": sentencepiece.__version__,
    }
    expected = {
        "transformers": "4.57.3",
        "huggingface_hub": "0.36.0",
        "safetensors": "0.6.2",
        "tokenizers": "0.22.1",
        "sentencepiece": "0.2.1",
    }
    if versions != expected:
        raise ValueError(f"inference package versions differ from protocol: {versions}")
    summary = learned_smoke(
        args.root / "configs/learned_smoke.json", args.root, args.output / "learned"
    )
    runtime = dict(versions, torch=torch.__version__, cuda=torch.version.cuda)
    summary["runtime"] = runtime
    write_json(args.output / "learned/summary.json", summary)
    manifest = read_json(args.output / "learned/manifest.json")
    manifest["runtime"] = runtime
    write_json(args.output / "learned/manifest.json", manifest)
    write_json(
        args.output / "completion.json",
        {
            "status": "phase1_retrieval_pilot_completed",
            "queries": summary["queries"],
            "cuda_available": torch.cuda.is_available(),
            "runtime": runtime,
            "gpus": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
            "published_baseline_reproduced": False,
            "llm_calls": 0,
        },
    )


if __name__ == "__main__":
    main()
