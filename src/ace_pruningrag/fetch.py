"""Download a pinned, hash-verified dataset without committing raw data."""

import urllib.request
from pathlib import Path
from typing import Any

from .dataset import DatasetError, verify_dataset


def fetch_dataset(config: dict[str, Any], root: Path) -> Path:
    destination = root / config["path"]
    if destination.exists():
        # Never replace existing bytes silently, including a corrupted download.
        return verify_dataset(config, root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    if temporary.exists():
        raise DatasetError(f"partial download exists; inspect/remove it before retry: {temporary}")
    url = (
        f"https://huggingface.co/datasets/{config['repository']}/resolve/"
        f"{config['revision']}/{config['filename']}"
    )
    with urllib.request.urlopen(url, timeout=60) as response, temporary.open("xb") as stream:
        total = 0
        while block := response.read(1024 * 1024):
            total += len(block)
            if total > config["bytes"]:
                raise DatasetError("download exceeds expected size")
            stream.write(block)
    temporary_config = dict(config, path=str(temporary))
    verify_dataset(temporary_config, root)
    temporary.rename(destination)
    return destination
