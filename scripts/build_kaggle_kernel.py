"""Bundle only allowlisted first-party source/configs into a private Kaggle kernel."""

import argparse
import base64
import hashlib
import json
import re
import zlib
from pathlib import Path


def build(root: Path, output: Path, owner: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", owner):
        raise ValueError("invalid Kaggle owner")
    paths = sorted((root / "src/ace_pruningrag").glob("*.py"))
    paths += [
        root / "configs" / name
        for name in (
            "dataset.json",
            "upstream.json",
            "retrieval_smoke.json",
        )
    ]
    files = {str(path.relative_to(root)): path.read_text(encoding="utf-8") for path in paths}
    hashes = {name: hashlib.sha256(value.encode()).hexdigest() for name, value in files.items()}
    payload = base64.b64encode(
        zlib.compress(
            json.dumps(
                {
                    "files": files,
                    "sha256": hashes,
                }
            ).encode()
        )
    ).decode()
    template = (root / "scripts/kaggle_bootstrap.py").read_text(encoding="utf-8")
    if template.count('PAYLOAD = "__BUNDLE__"') != 1:
        raise ValueError("bundle placeholder missing or repeated")
    source = template.replace('PAYLOAD = "__BUNDLE__"', f"PAYLOAD = {payload!r}")
    output.mkdir(parents=True, exist_ok=False)
    (output / "bootstrap.py").write_text(source, encoding="utf-8")
    metadata = {
        "id": f"{owner}/ace-pruningrag-phase1-bootstrap",
        "title": "ACE PruningRAG Phase1 Bootstrap",
        "code_file": "bootstrap.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "machine_shape": "NvidiaTeslaT4",
        "enable_internet": True,
        "dataset_sources": [],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    }
    (output / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (output / "bundle-manifest.json").write_text(json.dumps(hashes, indent=2) + "\n")
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(build(args.root.resolve(), args.output, args.owner), indent=2))
