"""Build a new private single-request Kaggle kernel, preserving all existing kernels."""

import argparse
import base64
import hashlib
import json
import re
import zlib
from pathlib import Path


def build(root, output, owner, request_id, qid):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", owner) or not re.fullmatch(r"[a-f0-9]{32}", request_id):
        raise ValueError("valid owner and unique 32-hex request identity required")
    if not re.fullmatch(r"[a-f0-9-]{36}", qid):
        raise ValueError("pinned interaction identity required")
    files = {
        str(p.relative_to(root)): p.read_text()
        for p in sorted((root / "src/ace_pruningrag").glob("*.py"))
    }
    for name in ("configs/dataset.json", "configs/generated_pilot.json", "scripts/live_driver.py"):
        files[name] = (root / name).read_text()
    files["configs/live_request.json"] = json.dumps(
        {"interaction_id": qid, "request_id": request_id}
    )
    hashes = {name: hashlib.sha256(content.encode()).hexdigest() for name, content in files.items()}
    payload = base64.b64encode(
        zlib.compress(json.dumps({"files": files, "sha256": hashes}).encode())
    ).decode()
    template = (root / "scripts/kaggle_generated_pilot.py").read_text()
    if template.count('PAYLOAD = "__BUNDLE__"') != 1:
        raise ValueError("live bundle placeholder differs")
    template = template.replace(
        'Path("/kaggle/working/phase3-pilot")', 'Path("/kaggle/working/live-answer")'
    )
    template = template.replace(
        'fetch_assets(read_json(root / "configs/crag_prices.json"), root)', ""
    )
    template = template.replace(
        "Dataset and original price snapshot verified",
        "Pinned dataset verified; live web-only request",
    )
    template = template.replace("scripts/generated_driver.py", "scripts/live_driver.py")
    template = template.replace('PAYLOAD = "__BUNDLE__"', f"PAYLOAD = {payload!r}")
    output.mkdir(parents=True, exist_ok=False)
    (output / "bootstrap.py").write_text(template)
    metadata = {
        "id": f"{owner}/ace-live-{request_id}",
        "title": f"ACE Live {request_id}",
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
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--owner", required=True)
    p.add_argument("--request-id", required=True)
    p.add_argument("--qid", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    build(Path.cwd(), a.output, a.owner, a.request_id, a.qid)
