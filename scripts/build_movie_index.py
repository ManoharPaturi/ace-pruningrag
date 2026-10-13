"""Build a bounded-memory movie snapshot index without changing original assets."""

import argparse
from pathlib import Path

from ace_pruningrag.artifacts import read_json, write_json
from ace_pruningrag.movie_snapshot import build_index

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    a = p.parse_args()
    if a.manifest.exists():
        raise FileExistsError(a.manifest)
    result = build_index(read_json(Path("configs/crag_movie.json")), Path.cwd(), a.output)
    write_json(a.manifest, result)
    print(result)
