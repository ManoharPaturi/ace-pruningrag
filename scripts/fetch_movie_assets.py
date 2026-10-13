"""Restore only the explicitly bounded, pinned original movie snapshot files."""

import argparse
from pathlib import Path

from ace_pruningrag.artifacts import read_json, write_json
from ace_pruningrag.assets import fetch_assets

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)
    write_json(a.output, fetch_assets(read_json(Path("configs/crag_movie.json")), Path.cwd()))
