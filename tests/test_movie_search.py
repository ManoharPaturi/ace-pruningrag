import json
import sqlite3

import pytest
from rank_bm25 import BM25Okapi

from ace_pruningrag.artifacts import sha256_file
from ace_pruningrag.movie_search import MovieNameSearch, build_search, normalize_name
from ace_pruningrag.movie_snapshot import MovieSnapshot, build_index


def setup(root, names=None):
    names = names or ["john smith", "john  smith", "john jones", "john paul", "jane doe"]
    source = {
        "movie_db.json": {"a film": {"id": 1}, "other story": {"id": 2}},
        "person_db.json": {n: {"id": i + 10, "name": n} for i, n in enumerate(names)},
        "year_db.json": {"2021": {"movie_list": [1, 2]}},
    }
    assets = []
    for name, data in source.items():
        p = root / name
        p.write_text(json.dumps(data))
        assets.append({"local_path": name, "bytes": p.stat().st_size, "sha256": sha256_file(p)})
    config = {"revision": "test", "assets": assets}
    record_index = root / "records.sqlite"
    proof = build_index(config, root, record_index)
    snapshot = MovieSnapshot(config, root, record_index, proof["index_sha256"])
    index = root / "search.sqlite"
    manifest = build_search(snapshot, index)
    search = MovieNameSearch(snapshot, index, manifest["search_index_sha256"])
    return names, snapshot, search, index, manifest


def test_numeric_scores_match_reference_including_negative_idf_and_repeated_terms(tmp_path):
    names, _, search, _, _ = setup(tmp_path)
    reference = BM25Okapi([n.split() for n in names])
    assert reference.idf["john"] == pytest.approx(0.25 * reference.average_idf)
    for query in ("John Smith", "John John", "JANE_DOE!", "unseenword"):
        expected = reference.get_scores(normalize_name(query).split())
        actual = {r["name"]: r["score"] for r in search.search("person", query)}
        for name, score in zip(names, expected, strict=True):
            if score == 0:
                assert name not in actual
            else:
                assert actual[name] == pytest.approx(score, rel=1e-12, abs=1e-12)


def test_ties_are_explicit_and_records_keep_their_own_names_and_ids(tmp_path):
    _, snapshot, search, _, manifest = setup(tmp_path)
    ranked = search.search("person", "john smith")
    assert ranked[0]["name"] == "john  smith"
    assert ranked[1]["name"] == "john smith"
    assert ranked[0]["record"]["id"] != ranked[1]["record"]["id"]
    assert manifest["parameters"]["tie_break"] == "source_rowid_desc"
    assert not manifest["semantic_identity_verified"]
    assert search.lookup("/movie/get_person_info", "john smith") == [r["record"] for r in ranked]
    assert search.lookup("/movie/get_movie_info_by_id", 1) == snapshot.lookup(
        "/movie/get_movie_info_by_id", 1
    )


def test_query_caps_unknown_terms_readonly_and_integrity_guards(tmp_path):
    _, snapshot, search, index, manifest = setup(tmp_path)
    assert search.search("person", "unseenword") == []
    for limit in (0, 11, True):
        with pytest.raises(ValueError):
            search.search("person", "john", limit)
    with pytest.raises(ValueError):
        MovieNameSearch(snapshot, index, "0" * 64)
    with search.connection() as db, pytest.raises(sqlite3.OperationalError, match="readonly"):
        db.execute("DELETE FROM terms")
    with pytest.raises(FileExistsError):
        build_search(snapshot, index)
    assert sha256_file(index) == manifest["search_index_sha256"]


def test_original_top_n_zero_filter_can_displace_negative_matches(tmp_path):
    names = ["a" + " " * i + "b" for i in range(1, 11)]
    names += ["a" + " " * i for i in range(5)] + ["b" + " " * i for i in range(5)]
    _, _, search, _, _ = setup(tmp_path, names)
    reference = BM25Okapi([name.split() for name in names])
    assert reference.average_idf < 0
    scores = reference.get_scores(["a"])
    assert sum(score == 0 for score in scores) == 5
    result = search.search("person", "a")
    assert len(result) == 5
    assert all(r["score"] < 0 for r in result)
