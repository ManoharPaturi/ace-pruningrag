"""Bundle only allowlisted first-party source/configs into a private Kaggle kernel."""

import argparse
import base64
import hashlib
import json
import re
import zlib
from pathlib import Path


def build(root: Path, output: Path, owner: str, mode: str = "bootstrap") -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", owner):
        raise ValueError("invalid Kaggle owner")
    if mode not in {"bootstrap", "retrieval", "generation"}:
        raise ValueError("unsupported kernel mode")
    paths = sorted((root / "src/ace_pruningrag").glob("*.py"))
    paths += [
        root / "configs" / name
        for name in (
            "dataset.json",
            "upstream.json",
            "retrieval_smoke.json",
        )
    ]
    if mode == "retrieval":
        paths += [
            root / "configs" / name
            for name in (
                "compatibility.json",
                "crag_finance.json",
                "learned_smoke.json",
            )
        ]
        paths.append(root / "scripts/learned_driver.py")
    if mode == "generation":
        paths += [root / "configs" / name for name in ("generated_pilot.json", "crag_prices.json")]
        paths.append(root / "scripts/generated_driver.py")
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
    template_name = {
        "bootstrap": "kaggle_bootstrap.py",
        "retrieval": "kaggle_retrieval_pilot.py",
        "generation": "kaggle_generated_pilot.py",
    }[mode]
    template = (root / "scripts" / template_name).read_text(encoding="utf-8")
    if template.count('PAYLOAD = "__BUNDLE__"') != 1:
        raise ValueError("bundle placeholder missing or repeated")
    source = template.replace('PAYLOAD = "__BUNDLE__"', f"PAYLOAD = {payload!r}")
    output.mkdir(parents=True, exist_ok=False)
    (output / "bootstrap.py").write_text(source, encoding="utf-8")
    metadata = {
        "id": f"{owner}/ace-pruningrag-phase1-"
        + ("bootstrap" if mode == "bootstrap" else "retrieval-pilot"),
        "title": "ACE PruningRAG Phase1 "
        + ("Bootstrap" if mode == "bootstrap" else "Retrieval Pilot"),
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
    if mode == "generation":
        metadata["id"] = f"{owner}/ace-pruningrag-phase3-generated-pilot"
        metadata["title"] = "ACE PruningRAG Phase3 Generated Pilot"
    (output / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (output / "bundle-manifest.json").write_text(json.dumps(hashes, indent=2) + "\n")
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--mode", choices=["bootstrap", "retrieval", "generation"], default="bootstrap"
    )
    args = parser.parse_args()
    print(json.dumps(build(args.root.resolve(), args.output, args.owner, args.mode), indent=2))
