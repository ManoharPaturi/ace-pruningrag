import bz2
import copy
import json

import pytest

from ace_pruningrag.artifacts import sha256_file
from ace_pruningrag.dataset import DatasetError, iter_records, validate_record, verify_dataset
from ace_pruningrag.fetch import fetch_dataset


def test_mixed_answers_preserved_and_gold_excluded(row):
    original = copy.deepcopy(row)
    record = validate_record(row)
    assert record.answers == ("2020",)
    assert record.raw == original
    inputs = record.inference_input()
    assert set(vars(inputs)) == {"interaction_id", "query", "query_time", "search_results"}
    inputs.search_results[0]["page_result"] = "changed copy"
    assert record.raw == original


def test_compressed_loader_and_duplicates_fail(row, tmp_path):
    path = tmp_path / "dataset.jsonl.bz2"
    with bz2.open(path, "wt") as stream:
        stream.write(json.dumps(row) + "\n")
    assert [r.interaction_id for r in iter_records(path)] == ["fixture-1"]
    with bz2.open(path, "wt") as stream:
        stream.write((json.dumps(row) + "\n") * 2)
    with pytest.raises(DatasetError, match=r":2: duplicate"):
        list(iter_records(path))


@pytest.mark.parametrize("suffix", ["\n", "not-json\n"])
def test_invalid_rows_never_silently_skipped(row, tmp_path, suffix):
    path = tmp_path / "dataset.jsonl"
    path.write_text(json.dumps(row) + "\n" + suffix)
    with pytest.raises(DatasetError, match=r":2:"):
        list(iter_records(path))


@pytest.mark.parametrize("answer", [None, True, {"value": 1}, float("nan")])
def test_reject_unsupported_answers(row, answer):
    row["answer"] = answer
    with pytest.raises(DatasetError):
        validate_record(row)


def test_page_validation(row):
    row["search_results"][0]["page_result"] = None
    with pytest.raises(DatasetError, match="page_result"):
        validate_record(row)


def test_hash_corruption_fails_and_fetch_preserves_existing_file(tmp_path):
    path = tmp_path / "data.bz2"
    path.write_bytes(b"original")
    config = {"path": "data.bz2", "bytes": 8, "sha256": sha256_file(path)}
    assert verify_dataset(config, tmp_path) == path
    path.write_bytes(b"modified")
    with pytest.raises(DatasetError, match="SHA-256"):
        fetch_dataset(config, tmp_path)
    assert path.read_bytes() == b"modified"
