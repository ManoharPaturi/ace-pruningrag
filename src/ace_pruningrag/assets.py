"""Bounded downloads of immutable, checksum-verified benchmark assets."""

import urllib.request
from pathlib import Path
from typing import Any

from .artifacts import sha256_file


def verify_asset(asset: dict[str, Any], root: Path) -> Path:
    path = root / asset["local_path"]
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("asset destination escapes repository root")
    if path.stat().st_size != asset["bytes"] or sha256_file(path) != asset["sha256"]:
        raise ValueError(f"asset integrity mismatch: {asset['local_path']}")
    return path


def fetch_assets(config: dict[str, Any], root: Path) -> dict[str, Any]:
    assets = config["assets"]
    total = sum(asset["bytes"] for asset in assets)
    if total > config["max_total_bytes"]:
        raise ValueError("asset set exceeds declared download budget")
    paths = [asset["local_path"] for asset in assets]
    if len(paths) != len(set(paths)):
        raise ValueError("duplicate asset destinations")
    for asset in assets:
        destination = root / asset["local_path"]
        if not destination.resolve().is_relative_to(root.resolve()):
            raise ValueError("asset destination escapes repository root")
        if destination.exists():
            verify_asset(asset, root)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_name(destination.name + ".part")
        if partial.exists():
            raise ValueError(f"inspect existing partial download before retry: {partial}")
        with urllib.request.urlopen(asset["url"], timeout=60) as response, partial.open("xb") as f:
            received = 0
            while block := response.read(1024 * 1024):
                received += len(block)
                if received > asset["bytes"]:
                    raise ValueError("download exceeds declared asset size")
                f.write(block)
        verify_asset(dict(asset, local_path=str(partial.relative_to(root))), root)
        partial.rename(destination)
    return {
        "status": "assets_verified",
        "assets": len(assets),
        "bytes": total,
        "revision": config["revision"],
        "scope": config["scope"],
    }
