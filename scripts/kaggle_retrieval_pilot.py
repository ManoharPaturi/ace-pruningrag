"""Restore a finance slice, check compatibility, and run the bounded BGE retrieval pilot."""

import base64
import hashlib
import importlib.metadata
import json
import subprocess
import sys
import zlib
from pathlib import Path

PAYLOAD = "__BUNDLE__"


def package_versions(names):
    versions = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


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
    package_names = (
        "transformers",
        "huggingface_hub",
        "tokenizers",
        "safetensors",
        "sentencepiece",
    )
    base_versions = package_versions(package_names)
    overlay = root / "inference-deps"
    # Install only the selected libraries in an isolated directory. The fresh
    # driver process prepends it; Kaggle's base environment is never modified.
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
    model_config = read_json(root / "configs/learned_smoke.json")
    print("Downloading pinned BGE weights (about 4.6 GB), temporary files only", flush=True)
    fetch_assets(model_config, root)
    subprocess.run(
        [
            sys.executable,
            str(root / "scripts/learned_driver.py"),
            "--root",
            str(root),
            "--overlay",
            str(overlay),
            "--output",
            str(output),
        ],
        check=True,
    )
    after = package_versions(package_names)
    if base_versions != after:
        raise ValueError("Kaggle base package versions changed")
    write_json(
        output / "environment_isolation.json",
        {
            "base_before": base_versions,
            "base_after": after,
            "base_preserved": True,
            "inference_packages": "isolated --target directory in a fresh process",
        },
    )


if __name__ == "__main__":
    main()
