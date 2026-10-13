import json

import pytest

from ace_pruningrag.artifacts import sha256_file
from ace_pruningrag.claim_extraction import digest
from ace_pruningrag.dataset import QueryInput
from ace_pruningrag.movie_evidence import retrieve_movie_evidence
from ace_pruningrag.movie_search import MovieNameSearch, build_search
from ace_pruningrag.movie_snapshot import MovieSnapshot, build_index
from ace_pruningrag.source_controls import prepare_source_controls


def fixture(root):
    movies = {name: {"id": i} for i, name in enumerate(("other story", "alpha", "beta", "gamma"))}
    movies["a film"] = {"id": 10, "director": ["A Director", "B Director"], "overview": "x " * 2000}
    sources = {
        "movie_db.json": movies,
        "person_db.json": {"a director": {"id": 20}},
        "year_db.json": {},
    }
    assets = []
    for name, value in sources.items():
        path = root / name
        path.write_text(json.dumps(value))
        assets.append(
            {
                "local_path": name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "url": f"https://example.org/{name}",
            }
        )
    config = {"revision": "test", "assets": assets}
    index = root / "records.sqlite"
    manifest = build_index(config, root, index)
    snapshot = MovieSnapshot(config, root, index, manifest["index_sha256"])
    names = root / "names.sqlite"
    name_proof = build_search(snapshot, names)
    search = MovieNameSearch(snapshot, names, name_proof["search_index_sha256"])
    query = QueryInput(
        "q",
        "Who directed A Film, or a film?",
        "2024",
        (
            {
                "page_result": "A Film director A Director.",
                "page_snippet": "",
                "page_url": "https://example.org/web",
                "page_name": "web",
                "page_last_modified": "",
            },
        ),
    )
    return query, search, config


def test_field_fidelity_caps_and_duplicate_source_fields_keep_both_request_links(tmp_path):
    query, search, config = fixture(tmp_path)
    requests = [{"kind": "movie", "span": x} for x in ("A Film", "a film")]
    items, audit = retrieve_movie_evidence(query, requests, search, config, max_field_chars=500)
    assert audit["source_calls"] == 2
    assert len(items) == len({e.evidence_id for e in items}) == 2
    directors = next(e for e in items if json.loads(e.content)["field"] == "director")
    assert json.loads(directors.content)["value"] == ["A Director", "B Director"]
    binding = audit["provenance"][directors.evidence_id]
    assert binding["field_value_sha256"] == digest(["A Director", "B Director"])
    assert binding["request_spans"] == ["A Film", "a film"]
    assert directors.char_start == 0 and directors.char_end == len(directors.content)
    assert binding["snapshot_observation_time"] is None
    assert not binding["semantic_identity_verified"] and not audit["answer_acceptance_enabled"]
    assert audit["excluded_fields"][0]["field"] == "overview"
    assert all(json.loads(e.content)["field"] != "overview" for e in items)


def test_invalid_name_proposals_and_caps_do_not_execute_lookups(tmp_path):
    query, search, config = fixture(tmp_path)
    for requests in (
        [{"kind": "movie", "span": "guessed film"}],
        [{"kind": "movie", "span": "A Fil"}],
        [{"kind": "movie", "span": "A Film", "gold": "label"}],
        [{"kind": "movie", "span": "A Film"}] * 2,
        [{"kind": "movie", "span": "A Film"}] * 3,
    ):
        with pytest.raises(ValueError):
            retrieve_movie_evidence(query, requests, search, config)
    with pytest.raises(ValueError):
        retrieve_movie_evidence(query, [], search, config, max_records=True)
    unknown = QueryInput("q", "unseenword", "2024", ())
    items, audit = retrieve_movie_evidence(
        unknown, [{"kind": "movie", "span": "unseenword"}], search, config
    )
    assert not items and audit["source_calls"] == 1
    assert audit["calls"][0]["returned_source_rowids"] == []


def test_shared_source_controls_preserve_pool_filters_and_full_budget(tmp_path):
    query, search, config = fixture(tmp_path)
    api, _ = retrieve_movie_evidence(
        query, [{"kind": "movie", "span": "A Film"}], search, config, max_field_chars=500
    )
    settings = {
        "candidate_limit": 12,
        "chunk_words": 100,
        "system_prompt": "Use evidence.",
        "max_new_tokens": 96,
        "total_tokens": 500,
        "max_items": 5,
    }

    # Character count exposes omission of the full provenance/chat wrapper from budgets.
    def tokenize(msg):
        return list(json.dumps(msg))

    requests, audit = prepare_source_controls(query, api, settings, tokenize)
    assert len(requests) == 6
    assert audit["shared_candidate_counts"] == {"web": 1, "api": 2}
    for mode in ("web_only", "api_only", "combined"):
        for method in ("top_k", "joint"):
            row = requests[f"{mode}/{method}"]
            assert set(row["candidate_ids"]) <= set(audit["shared_candidate_ids"])
            assert row["full_reserved_tokens"] == len(tokenize(row["messages"])) + 96 <= 500
            assert (
                all(e["source_kind"] == "web" for e in row["selected"])
                if mode == "web_only"
                else True
            )
            assert (
                all(e["source_kind"] == "api" for e in row["selected"])
                if mode == "api_only"
                else True
            )
            assert row["groups"] == [] and not row["semantic_support_verified"]
    with pytest.raises(ValueError, match="same query"):
        prepare_source_controls(
            QueryInput("other", query.query, query.query_time, ()), api, settings, tokenize
        )
    with pytest.raises(ValueError, match="duplicate"):
        prepare_source_controls(query, api + api, settings, tokenize)
    with pytest.raises(ValueError, match="full prompt"):
        prepare_source_controls(query, api, {**settings, "total_tokens": 1}, tokenize)
