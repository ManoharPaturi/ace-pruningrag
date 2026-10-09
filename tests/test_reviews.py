import copy
import json

import pytest

from ace_pruningrag.artifacts import sha256_file
from ace_pruningrag.reviews import import_review, validate_review_export


def fixture(row, tmp_path):
    dataset = tmp_path / "data.jsonl"
    dataset.write_text(json.dumps(row) + "\n")
    config = {"path": "data.jsonl", "bytes": dataset.stat().st_size, "sha256": sha256_file(dataset)}
    page = row["search_results"][0]
    quote = page["page_result"][:5]
    draft = {
        "interaction_id": row["interaction_id"],
        "query": row["query"],
        "status": "ai_assisted_draft",
        "human_validated": False,
        "references": [
            {
                "page_index": 0,
                "field": "page_result",
                "char_start": 0,
                "char_end": 5,
                "source_url": page["page_url"],
                "quote": quote,
            }
        ],
    }
    record = {
        "interaction_id": row["interaction_id"],
        "status": "reviewed",
        "notes": "My actual decision",
        "attested": True,
        "inspected_excerpts": [True],
        "human_validated": True,
        "draft": draft,
    }
    export = {
        "artifact_type": "human_review_of_ai_drafts",
        "reviewer": "Human Fixture",
        "reviews": [record],
    }
    path = tmp_path / "export.json"
    path.write_text(json.dumps(export))
    return path, config, export


def test_immutable_import_preserves_notes_and_does_not_admit_quality_labels(row, tmp_path):
    path, config, _ = fixture(row, tmp_path)
    original = path.read_bytes()
    result = import_review(path, config, tmp_path, tmp_path / "import")
    assert (tmp_path / "import/original-export.json").read_bytes() == original
    assert path.read_bytes() == original
    assert result["decisions"] == {"reviewed": 1}
    assert result["complete_evidence_labels_available"] is False
    with pytest.raises(FileExistsError):
        import_review(path, config, tmp_path, tmp_path / "import")


@pytest.mark.parametrize(
    "change", ["quote", "attested", "inspection", "identity", "duplicate", "flag"]
)
def test_invalid_export_rejected(row, tmp_path, change):
    path, config, export = fixture(row, tmp_path)
    r = export["reviews"][0]
    if change == "quote":
        r["draft"]["references"][0]["quote"] = "wrong quote"
    elif change == "attested":
        r["attested"] = False
    elif change == "inspection":
        r["inspected_excerpts"] = [False]
    elif change == "identity":
        r["draft"]["query"] = "changed question"
    elif change == "duplicate":
        export["reviews"].append(copy.deepcopy(r))
    elif change == "flag":
        r["human_validated"] = False
    path.write_text(json.dumps(export))
    with pytest.raises(ValueError):
        validate_review_export(path, config, tmp_path)
