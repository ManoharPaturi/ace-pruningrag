"""Restore a finance slice, check compatibility, and run the bounded BGE retrieval pilot."""

import base64
import hashlib
import json
import os
import subprocess
import sys
import zlib
from pathlib import Path

PAYLOAD = "__BUNDLE__"


def main():
    root = Path("/tmp/ace-pruningrag-pilot")
    root.mkdir(parents=True, exist_ok=False)
    output = Path("/kaggle/working/phase1-pilot")
    output.mkdir(parents=True, exist_ok=False)
    bundle = json.loads(zlib.decompress(base64.b64decode(PAYLOAD)))
    for name, content in bundle["files"].items():
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("unsafe bundle path")
        if hashlib.sha256(content.encode()).hexdigest() != bundle["sha256"][name]:
            raise ValueError("bundle checksum mismatch")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    sys.path.insert(0, str(root / "src"))
    from ace_pruningrag.artifacts import read_json, write_json
    from ace_pruningrag.assets import fetch_assets
    from ace_pruningrag.compatibility import prepare_compatibility
    from ace_pruningrag.fetch import fetch_dataset
    from ace_pruningrag.finance_api import finance_smoke
    from ace_pruningrag.upstream import checkout_upstream

    write_json(output / "bundle_manifest.json", bundle["sha256"])
    config = read_json(root / "configs/upstream.json")
    checkout_upstream(config, root)
    manifest = prepare_compatibility(
        config,
        read_json(root / "configs/compatibility.json"),
        root,
        root / ".cache/compatibility",
    )
    write_json(output / "compatibility.json", manifest)
    finance_config = read_json(root / "configs/crag_finance.json")
    fetch_assets(finance_config, root)
    write_json(output / "finance_smoke.json", finance_smoke(finance_config, root))
    fetch_dataset(read_json(root / "configs/dataset.json"), root)
    print("Compatibility copy and real finance API probes passed", flush=True)
    # Pin the small inference stack, preserving Kaggle's installed CUDA/PyTorch runtime.
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--quiet",
            "transformers==4.57.3",
            "huggingface_hub==0.36.0",
            "tokenizers==0.22.1",
            "safetensors==0.6.2",
            "sentencepiece==0.2.1",
        ],
        check=True,
    )
    os.environ["USE_TF"] = "0"
    os.environ["USE_FLAX"] = "0"
    model_config = read_json(root / "configs/learned_smoke.json")
    print("Downloading pinned BGE weights (about 4.6 GB), temporary files only", flush=True)
    fetch_assets(model_config, root)
    from ace_pruningrag.learned_retrieval import learned_smoke

    summary = learned_smoke(root / "configs/learned_smoke.json", root, output / "learned")
    import torch

    write_json(
        output / "completion.json",
        {
            "status": "phase1_retrieval_pilot_completed",
            "queries": summary["queries"],
            "cuda_available": torch.cuda.is_available(),
            "torch_version": torch.__version__,
            "gpus": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
            "published_baseline_reproduced": False,
            "llm_calls": 0,
        },
    )


if __name__ == "__main__":
    main()
