"""Probe actual restored records over loopback HTTP with original source comparisons."""

import argparse
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.claim_extraction import digest
from ace_pruningrag.movie_snapshot import MovieSnapshot, handler_for, object_records


def smoke(root, index, manifest):
    config, proof = read_json(root / "configs/crag_movie.json"), read_json(manifest)
    snapshot = MovieSnapshot(config, root, index, proof["index_sha256"])
    expected = []
    for filename, endpoint in (
        ("movie_db.json", "/movie/get_movie_info_by_id"),
        ("person_db.json", "/movie/get_person_info_by_id"),
    ):
        selected_id, selected = None, None
        for _, record in object_records(root / "data/crag/movie" / filename):
            if selected_id is None and type(record.get("id")) is int:
                selected_id = record["id"]
            if record.get("id") == selected_id:
                selected = record
        if selected_id is None:
            raise ValueError("real snapshot has no probe entity ID")
        expected.append((endpoint, selected_id, selected))
    years = read_json(root / "data/crag/movie/year_db.json")
    expected.append(("/movie/get_year_info", "1990", years["1990"]))
    expected.append(("/movie/get_movie_info_by_id", -999999999, None))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(snapshot))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    probes = []
    try:
        for endpoint, query, source_record in expected:
            req = urllib.request.Request(
                f"http://127.0.0.1:{server.server_port}{endpoint}",
                data=json.dumps({"query": query}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                payload = json.load(response)
            if payload != {"result": source_record}:
                raise ValueError("HTTP movie result differs from original snapshot record")
            probes.append(
                {
                    "endpoint": endpoint,
                    "query": query,
                    "result_sha256": digest(payload["result"]),
                    "matches_original_snapshot": True,
                }
            )
        errors = []
        for endpoint, query, status in (
            ("/movie/get_year_info", "2024", 400),
            ("/movie/get_movie_info", "GoodFellas", 404),
            ("/movie/get_person_info_by_id", True, 400),
        ):
            req = urllib.request.Request(
                f"http://127.0.0.1:{server.server_port}{endpoint}",
                data=json.dumps({"query": query}).encode(),
            )
            try:
                urllib.request.urlopen(req, timeout=10)
            except urllib.error.HTTPError as exc:
                if exc.code != status:
                    raise ValueError("movie error probe status differs") from exc
            else:
                raise ValueError("unsupported movie query unexpectedly succeeded")
            errors.append({"endpoint": endpoint, "query": query, "status": status})
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return {
        "status": "movie_id_year_snapshot_HTTP_verified",
        "revision": config["revision"],
        "record_counts": proof["record_counts"],
        "repeated_id_records": proof["repeated_id_records"],
        "index_sha256": sha256_file(index),
        "index_manifest_sha256": sha256_file(manifest),
        "successful_probes": probes,
        "rejected_query_probes": errors,
        "name_search_implemented": False,
        "web_API_integration_verified": False,
        "cross_source_benefit_established": False,
        "external_truth_verified": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--index", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)
    write_json(a.output, smoke(Path.cwd(), a.index, a.manifest))
