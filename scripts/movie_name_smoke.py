"""Compare real name-search scores to the pinned reference and exercise HTTP."""

import argparse
import importlib.metadata
import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import numpy as np
import rank_bm25
from rank_bm25 import BM25Okapi

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.claim_extraction import digest
from ace_pruningrag.movie_search import MovieNameSearch, normalize_name
from ace_pruningrag.movie_snapshot import MovieSnapshot, handler_for


def smoke(root, records_index, records_manifest, names_index, names_manifest):
    snapshot = MovieSnapshot(
        read_json(root / "configs/crag_movie.json"),
        root,
        records_index,
        read_json(records_manifest)["index_sha256"],
    )
    search = MovieNameSearch(
        snapshot, names_index, read_json(names_manifest)["search_index_sha256"]
    )
    if importlib.metadata.version("rank-bm25") != "0.2.2":
        raise ValueError("name-search reference version differs")
    probes = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(search))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for kind, queries in (
            ("movie", ["GoodFellas", "Fifty Dead Men Walking", "zzzzunseenwordqqqq"]),
            ("person", ["Tony Todd", "Damon Russell", "Robert Downey Jr.", "Tom_Cruise"]),
        ):
            with snapshot.connection() as db:
                names = list(
                    db.execute(
                        "SELECT rowid,name FROM records WHERE kind=? ORDER BY rowid", (kind,)
                    )
                )
            positions = {docid: i for i, (docid, _) in enumerate(names)}
            reference = BM25Okapi([name.split() for _, name in names])
            for query in queries:
                values = reference.get_scores(normalize_name(query).split())
                actual = search.search(kind, query)
                errors = [
                    abs(row["score"] - float(values[positions[row["source_rowid"]]]))
                    for row in actual
                ]
                if any(error > 1e-12 for error in errors):
                    raise ValueError("real name score differs from reference")
                original_ids = [
                    names[i][0] for i in np.argsort(values)[::-1][:10] if values[i] != 0
                ]
                original_scores = [float(values[positions[i]]) for i in original_ids]
                if len(original_scores) != len(actual) or any(
                    abs(expected - row["score"]) > 1e-12
                    for expected, row in zip(original_scores, actual, strict=True)
                ):
                    raise ValueError("name-search ranked score sequence differs")
                endpoint = "/movie/get_movie_info" if kind == "movie" else "/movie/get_person_info"
                req = urllib.request.Request(
                    f"http://127.0.0.1:{server.server_port}{endpoint}",
                    data=json.dumps({"query": query}).encode(),
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    payload = json.load(response)
                with snapshot.connection() as db:
                    source_records = [
                        json.loads(
                            db.execute(
                                "SELECT payload FROM records WHERE rowid=?", (r["source_rowid"],)
                            ).fetchone()[0]
                        )
                        for r in actual
                    ]
                if payload != {"result": source_records}:
                    raise ValueError("name HTTP payload differs from original stored records")
                probes.append(
                    {
                        "kind": kind,
                        "query": query,
                        "results": len(actual),
                        "maximum_returned_score_error": max(errors, default=0.0),
                        "ranked_source_ids_equal_to_numpy_reference": original_ids
                        == [r["source_rowid"] for r in actual],
                        "ranked_score_sequence_matches_reference": True,
                        "response_sha256": digest(payload),
                        "HTTP_records_match_source": True,
                    }
                )
            del reference, names, positions
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return {
        "status": "movie_name_scores_and_HTTP_records_verified",
        "source_index_sha256": sha256_file(records_index),
        "name_index_sha256": sha256_file(names_index),
        "name_manifest_sha256": sha256_file(names_manifest),
        "reference_version": importlib.metadata.version("rank-bm25"),
        "reference_source_sha256": sha256_file(Path(rank_bm25.__file__)),
        "probes": probes,
        "tie_break": search.metadata["parameters"]["tie_break"],
        "all_rankings_equal_to_numpy_reference": all(
            p["ranked_source_ids_equal_to_numpy_reference"] for p in probes
        ),
        "semantic_identity_verified": False,
        "cross_source_benefit_established": False,
        "additional_model_calls": 0,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--records", type=Path, required=True)
    p.add_argument("--records-manifest", type=Path, required=True)
    p.add_argument("--names", type=Path, required=True)
    p.add_argument("--names-manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)
    write_json(
        a.output, smoke(Path.cwd(), a.records, a.records_manifest, a.names, a.names_manifest)
    )
