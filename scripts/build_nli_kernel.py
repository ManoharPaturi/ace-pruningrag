"""Private bounded post-hoc NLI run; payload excludes gold labels and credentials."""

import argparse
import base64
import hashlib
import json
import uuid
import zlib
from pathlib import Path

from ace_pruningrag.nli_diagnostic import answer_source_pairs


def build(root, trace, output, owner):
    import re

    if not re.fullmatch(r"[A-Za-z0-9_-]+", owner):
        raise ValueError("invalid NLI kernel owner")
    config = json.loads((root / "configs/nli_diagnostic.json").read_text())
    rows = [json.loads(line) for line in trace.read_text().splitlines()]
    pairs = answer_source_pairs(rows, config["max_pairs"])
    source_sha = hashlib.sha256(trace.read_bytes()).hexdigest()
    files = {
        str(p.relative_to(root)): p.read_text()
        for p in sorted((root / "src/ace_pruningrag").glob("*.py"))
    }
    for name in ("configs/nli_diagnostic.json", "scripts/nli_driver.py"):
        files[name] = (root / name).read_text()
    files["configs/nli_pairs.json"] = json.dumps(
        {"source_trace_sha256": source_sha, "pairs": pairs}, ensure_ascii=False
    )
    hashes = {name: hashlib.sha256(content.encode()).hexdigest() for name, content in files.items()}
    payload = base64.b64encode(
        zlib.compress(json.dumps({"files": files, "sha256": hashes}).encode())
    ).decode()
    template = (root / "scripts/kaggle_generated_pilot.py").read_text()
    if template.count('PAYLOAD = "__BUNDLE__"') != 1:
        raise ValueError("NLI bundle placeholder differs")
    template = template.replace('fetch_dataset(read_json(root / "configs/dataset.json"), root)', "")
    template = template.replace(
        'fetch_assets(read_json(root / "configs/crag_prices.json"), root)', ""
    )
    template = template.replace(
        'fetch_assets(read_json(root / "configs/generated_pilot.json"), root)',
        'fetch_assets(read_json(root / "configs/nli_diagnostic.json"), root)',
    )
    template = template.replace("scripts/generated_driver.py", "scripts/nli_driver.py")
    template = template.replace(
        'Path("/kaggle/working/phase3-pilot")', 'Path("/kaggle/working/nli-pilot")'
    )
    template = template.replace(
        "Dataset and original price snapshot verified",
        "Frozen source/answer pairs bundled; no new retrieval",
    )
    template = template.replace(
        "Pinned Qwen generator weights verified",
        "Pinned independent NLI classifier weights verified",
    )
    template = template.replace('PAYLOAD = "__BUNDLE__"', f"PAYLOAD = {payload!r}")
    output.mkdir(parents=True, exist_ok=False)
    (output / "bootstrap.py").write_text(template)
    identity = uuid.uuid4().hex
    metadata = {
        "id": f"{owner}/ace-nli-{identity}",
        "title": f"ACE NLI {identity}",
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
    (output / "pair-manifest.json").write_text(
        json.dumps(
            {
                "pairs": len(pairs),
                "source_trace_sha256": source_sha,
                "pairs_sha256": hashes["configs/nli_pairs.json"],
                "kernel_id": metadata["id"],
                "max_tokens_per_pair": 512,
                "max_forward_calls": 79,
                "new_generation_calls": 0,
            },
            indent=2,
        )
        + "\n"
    )
    return metadata


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--trace", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--owner", required=True)
    a = p.parse_args()
    print(json.dumps(build(Path.cwd(), a.trace, a.output, a.owner)))
