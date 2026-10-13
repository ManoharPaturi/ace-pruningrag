import json
import sqlite3
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from ace_pruningrag.artifacts import sha256_file
from ace_pruningrag.movie_snapshot import MovieSnapshot, build_index, handler_for, object_records


def fixtures(root):
    rows = {
        "movie_db.json": {
            "alpha": {"id": 1, "title": "Alpha"},
            "alias": {"id": 1, "title": "Alias"},
        },
        "person_db.json": {"person": {"id": 2, "name": "P", "birth_date": None}},
        "year_db.json": {"2021": {"movie_list": [1], "oscar_awards": [{"winner": False}]}},
    }
    assets = []
    for name, data in rows.items():
        path = root / name
        path.write_text(json.dumps(data))
        assets.append(
            {"local_path": name, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        )
    return {"assets": assets, "revision": "test"}


def test_streaming_preserves_unicode_and_escaped_strings_across_small_chunks(tmp_path):
    p = tmp_path / "records.json"
    data = {"é": {"id": 1, "name": 'A "quote"', "nested": [None, True, {"x": "\n"}]}}
    p.write_text(json.dumps(data, ensure_ascii=False))
    assert dict(object_records(p, chunk_size=1)) == data
    p.write_text("{} trailing")
    with pytest.raises(ValueError, match="trailing"):
        list(object_records(p, chunk_size=1))
    p.write_text('{"a":{"x":NaN}}')
    with pytest.raises(ValueError, match="nonfinite"):
        list(object_records(p, chunk_size=1))
    p.write_text('{"a":{"x":"too long"}}')
    with pytest.raises(ValueError, match="size cap"):
        list(object_records(p, chunk_size=100, max_record_chars=4))


def test_exact_id_lookup_preserves_original_last_record_and_nomination_flags(tmp_path):
    cfg = fixtures(tmp_path)
    index = tmp_path / "index.sqlite"
    proof = build_index(cfg, tmp_path, index)
    assert proof["record_counts"] == {"movie": 2, "person": 1, "year": 1}
    assert proof["repeated_id_records"]["movie"] == 1
    snapshot = MovieSnapshot(cfg, tmp_path, index, proof["index_sha256"])
    assert snapshot.lookup("/movie/get_movie_info_by_id", 1)["title"] == "Alias"
    assert snapshot.lookup("/movie/get_person_info_by_id", 2)["birth_date"] is None
    assert not snapshot.lookup("/movie/get_year_info", "2021")["oscar_awards"][0]["winner"]
    assert snapshot.lookup("/movie/get_movie_info_by_id", 999) is None
    assert snapshot.lookup("/movie/get_movie_info_by_id", 2**100) is None
    with snapshot.connection() as db, pytest.raises(sqlite3.OperationalError, match="readonly"):
        db.execute("DELETE FROM records")
    for endpoint, query in (
        ("/movie/get_year_info", "2024"),
        ("/movie/get_movie_info_by_id", True),
    ):
        with pytest.raises(ValueError):
            snapshot.lookup(endpoint, query)
    with pytest.raises(KeyError):
        snapshot.lookup("/movie/get_movie_info", "Alpha")
    with pytest.raises(FileExistsError):
        build_index(cfg, tmp_path, index)


def test_snapshot_and_index_tampering_are_rejected(tmp_path):
    cfg = fixtures(tmp_path)
    index = tmp_path / "index.sqlite"
    proof = build_index(cfg, tmp_path, index)
    with pytest.raises(ValueError, match="checksum"):
        MovieSnapshot(cfg, tmp_path, index, "0" * 64)
    (tmp_path / "movie_db.json").write_text("{}")
    with pytest.raises(ValueError, match="integrity"):
        MovieSnapshot(cfg, tmp_path, index, proof["index_sha256"])


def test_original_valid_wire_shapes_and_explicit_unsupported_endpoints(tmp_path):
    cfg = fixtures(tmp_path)
    index = tmp_path / "index.sqlite"
    proof = build_index(cfg, tmp_path, index)
    snapshot = MovieSnapshot(cfg, tmp_path, index, proof["index_sha256"])
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(snapshot))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for endpoint, query in (
            ("/movie/get_movie_info_by_id", 1),
            ("/movie/get_year_info", "2021"),
        ):
            request = urllib.request.Request(
                f"http://127.0.0.1:{server.server_port}{endpoint}",
                data=json.dumps({"query": query}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                assert json.load(response) == {"result": snapshot.lookup(endpoint, query)}
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}/movie/get_movie_info",
            data=b'{"query":"Alpha"}',
        )
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(request, timeout=5)
        assert exc.value.code == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
