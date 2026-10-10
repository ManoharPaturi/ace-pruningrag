import copy
import importlib.util
from pathlib import Path

import pytest

from ace_pruningrag.artifacts import write_json
from ace_pruningrag.dataset import QueryInput
from ace_pruningrag.prospective import (
    canonical_url,
    exposed_ids,
    sample_queries,
    validate_decisions,
)


def q(identity, query=None, url=None):
    return QueryInput(
        identity,
        query or identity,
        "02/28/2024, 09:00:00 PT",
        (
            {
                "page_url": url or "https://example.invalid/" + identity,
                "page_result": "source",
                "page_snippet": "",
                "page_name": "source",
                "page_last_modified": "",
            },
        ),
    )


def test_sampler_excludes_prior_text_and_canonical_url_overlap():
    rows = [
        q("old", "shared question", "https://www.example.invalid/page#part"),
        q("same-text", "SHARED QUESTION?"),
        q("same-url", url="http://example.invalid/page/"),
        q("new-one"),
        q("new-two"),
        q("new-three"),
    ]
    chosen, _ = sample_queries(rows, {"old"}, "seed", 2)
    assert {x.interaction_id for x in chosen} <= {"new-one", "new-two", "new-three"}
    assert [x.interaction_id for x in chosen] == [
        x.interaction_id for x in sample_queries(list(reversed(rows)), {"old"}, "seed", 2)[0]
    ]
    with pytest.raises(ValueError):
        sample_queries(rows, {"unknown"}, "seed", 1)
    with pytest.raises(ValueError):
        sample_queries(rows, {"old"}, "seed", 10)


def test_source_overlap_within_sample_and_query_parameters():
    rows = [
        q("a", url="https://example.invalid/same"),
        q("b", url="https://www.example.invalid/same#x"),
        q("c"),
    ]
    chosen, _ = sample_queries(rows, set(), "seed", 2)
    assert len({canonical_url(x.search_results[0]["page_url"]) for x in chosen}) == 2
    assert canonical_url("https://example.invalid/article?id=1") != canonical_url(
        "https://example.invalid/article?id=2"
    )
    assert exposed_ids(
        {"nested": [{"query_ids": ["a"]}, {"interaction_id": "b"}], "evidence_id": "not-a-question"}
    ) == {"a", "b"}


def review():
    packet = {
        "questions": [
            {"interaction_id": "q", "candidates": [{"evidence_id": "a"}, {"evidence_id": "b"}]}
        ]
    }
    export = {
        "artifact_type": "human_candidate_evidence_review",
        "packet_sha256": "hash",
        "reviewer": "Human",
        "reviews": [
            {
                "interaction_id": "q",
                "status": "reviewed",
                "answerability": "supported_by_candidates",
                "requirements": "Two facts",
                "notes": "",
                "attested": True,
                "acceptable_sets": [["a", "b"]],
            }
        ],
    }
    return packet, export


def test_complete_support_review_and_unresolved_bounds():
    packet, export = review()
    result = validate_decisions(export, packet, "hash")
    assert result["complete_human_candidate_review"]
    assert not result["publication_evaluation_ready"]
    export["reviews"][0]["status"] = "needs_changes"
    assert validate_decisions(export, packet, "hash")["unresolved_questions"] == 1
    export["reviews"][0].update(
        answerability="missing_evidence", acceptable_sets=[], status="reviewed"
    )
    assert validate_decisions(export, packet, "hash")["complete_human_candidate_review"]


@pytest.mark.parametrize(
    "mutation",
    [
        "wrong_packet",
        "unattested",
        "no_requirements",
        "unknown_span",
        "duplicate_span",
        "duplicate_set",
        "unknown_id",
        "duplicate_review",
        "contradiction",
        "bad_span_type",
    ],
)
def test_review_rejects_invalid_labels(mutation):
    packet, export = review()
    row = export["reviews"][0]
    if mutation == "wrong_packet":
        export["packet_sha256"] = "other"
    elif mutation == "unattested":
        row["attested"] = False
    elif mutation == "no_requirements":
        row["requirements"] = " "
    elif mutation == "unknown_span":
        row["acceptable_sets"] = [["unknown"]]
    elif mutation == "duplicate_span":
        row["acceptable_sets"] = [["a", "a"]]
    elif mutation == "duplicate_set":
        row["acceptable_sets"] = [["a", "b"], ["b", "a"]]
    elif mutation == "unknown_id":
        row["interaction_id"] = "other"
    elif mutation == "duplicate_review":
        export["reviews"].append(copy.deepcopy(row))
    elif mutation == "contradiction":
        row["answerability"] = "missing_evidence"
    else:
        row["acceptable_sets"] = [[{}]]
    with pytest.raises(ValueError):
        validate_decisions(export, packet, "hash")


def test_source_review_escapes_untrusted_page_and_has_pending_decisions(tmp_path):
    root = Path(__file__).parents[1]
    spec = importlib.util.spec_from_file_location(
        "builder", root / "scripts/build_evidence_review.py"
    )
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    payload = '</script><script>alert("fixture")</script>'
    packet = {
        "questions": [
            {
                "interaction_id": "q",
                "query": payload,
                "query_time": "time",
                "pages": [
                    {
                        "page_name": "page",
                        "page_url": "url",
                        "page_result": payload,
                        "page_snippet": "",
                    }
                ],
                "candidates": [
                    {
                        "evidence_id": "a",
                        "source_title": "source",
                        "source_url": "url",
                        "page_index": 0,
                        "field": "page_result",
                        "char_start": 0,
                        "char_end": len(payload),
                        "content": payload,
                    }
                ],
            }
        ]
    }
    path = tmp_path / "packet.json"
    write_json(path, packet)
    out = tmp_path / "review.html"
    builder.build(path, out)
    page = out.read_text()
    assert payload not in page and "&lt;/script&gt;" in page
    assert "1 fresh questions" in page
    assert '<option value="pending">Pending</option>' in page
