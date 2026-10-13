"""Build name postings over the original verified disk-backed movie records."""

import argparse
from pathlib import Path

from ace_pruningrag.artifacts import read_json, write_json
from ace_pruningrag.movie_search import build_search
from ace_pruningrag.movie_snapshot import MovieSnapshot

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--records", type=Path, required=True)
    p.add_argument("--records-manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    a = p.parse_args()
    if a.manifest.exists():
        raise FileExistsError(a.manifest)
    snapshot = MovieSnapshot(
        read_json(Path("configs/crag_movie.json")),
        Path.cwd(),
        a.records,
        read_json(a.records_manifest)["index_sha256"],
    )
    result = build_search(snapshot, a.output)
    write_json(a.manifest, result)
    print(result)
