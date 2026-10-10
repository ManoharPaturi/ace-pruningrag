"""Private bounded generation job; only pinned files and isolated inference packages."""

import base64
import hashlib
import importlib.metadata
import json
import subprocess
import sys
import zlib
from pathlib import Path

PAYLOAD = "__BUNDLE__"


def main():
    root = Path("/tmp/ace-pruningrag-generated")
    root.mkdir(exist_ok=False)
    output = Path("/kaggle/working/phase3-pilot")
    output.mkdir(exist_ok=False)
    bundle = json.loads(zlib.decompress(base64.b64decode(PAYLOAD)))
    for name, content in bundle["files"].items():
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("unsafe path")
        if hashlib.sha256(content.encode()).hexdigest() != bundle["sha256"][name]:
            raise ValueError("bundle mismatch")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    sys.path.insert(0, str(root / "src"))
    from ace_pruningrag.artifacts import read_json, write_json
    from ace_pruningrag.assets import fetch_assets
    from ace_pruningrag.fetch import fetch_dataset

    write_json(output / "bundle_manifest.json", bundle["sha256"])
    fetch_dataset(read_json(root / "configs/dataset.json"), root)
    fetch_assets(read_json(root / "configs/crag_prices.json"), root)
    print("Dataset and original price snapshot verified", flush=True)
    fetch_assets(read_json(root / "configs/generated_pilot.json"), root)
    print("Pinned Qwen generator weights verified", flush=True)
    packages = ["transformers", "huggingface_hub", "tokenizers", "safetensors", "sentencepiece"]
    before = {name: importlib.metadata.version(name) for name in packages}
    overlay = root / "inference-deps"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--quiet",
            "--no-deps",
            "--target",
            str(overlay),
            "transformers==4.57.3",
            "huggingface_hub==0.36.0",
            "tokenizers==0.22.1",
            "safetensors==0.6.2",
            "sentencepiece==0.2.1",
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(root / "scripts/generated_driver.py"),
            "--root",
            str(root),
            "--overlay",
            str(overlay),
            "--output",
            str(output),
        ],
        check=True,
    )
    after = {name: importlib.metadata.version(name) for name in packages}
    if before != after:
        raise ValueError("base environment changed")
    write_json(
        output / "environment_isolation.json",
        {"base_before": before, "base_after": after, "base_preserved": True},
    )


if __name__ == "__main__":
    main()
