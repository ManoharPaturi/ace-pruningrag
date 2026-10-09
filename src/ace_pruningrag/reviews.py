"""Validate human decisions over AI drafts without manufacturing evidence labels."""

from collections import Counter
from pathlib import Path

from .artifacts import read_json, sha256_file, write_json
from .dataset import iter_records, verify_dataset


def validate_review_export(export_path: Path, dataset_config: dict, root: Path) -> dict:
    export = read_json(export_path)
    if export.get("artifact_type") != "human_review_of_ai_drafts":
        raise ValueError("unexpected review artifact type")
    if not isinstance(export.get("reviewer"), str) or not export["reviewer"].strip():
        raise ValueError("reviewer identity required")
    rows = export.get("reviews")
    if not isinstance(rows, list) or not rows:
        raise ValueError("nonempty reviews required")
    ids = [row["interaction_id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate reviewed query IDs")
    wanted = set(ids)
    records = {
        record.interaction_id: record.inference_input()
        for record in iter_records(verify_dataset(dataset_config, root))
        if record.interaction_id in wanted
    }
    if set(records) != wanted:
        raise ValueError("reviewed queries missing from pinned dataset")
    references = 0
    for row in rows:
        if row["status"] not in ("pending", "reviewed", "needs_changes"):
            raise ValueError("unknown review status")
        if type(row.get("human_validated")) is not bool:
            raise ValueError("explicit validation flag required")
        if row["human_validated"] != (row["status"] == "reviewed"):
            raise ValueError("validation flag contradicts decision")
        if not isinstance(row.get("notes"), str):
            raise ValueError("notes must be text")
        draft = row["draft"]
        query = records[row["interaction_id"]]
        if draft["interaction_id"] != query.interaction_id or draft["query"] != query.query:
            raise ValueError("draft identity/query differs from pinned input")
        if draft.get("human_validated") is not False or draft.get("status") != "ai_assisted_draft":
            raise ValueError("embedded draft must retain its AI-assisted status")
        refs = draft["references"]
        inspected = row["inspected_excerpts"]
        if len(inspected) != len(refs) or any(type(value) is not bool for value in inspected):
            raise ValueError("inspection flags must match reference list")
        if row["status"] == "reviewed" and (row.get("attested") is not True or not all(inspected)):
            raise ValueError("reviewed decision needs attestation and inspected references")
        for ref in refs:
            index, start, end = ref["page_index"], ref["char_start"], ref["char_end"]
            if any(type(value) is not int for value in (index, start, end)):
                raise ValueError("reference coordinates must be integers")
            if not 0 <= index < len(query.search_results):
                raise ValueError("reference page out of range")
            page = query.search_results[index]
            if ref["field"] not in ("page_result", "page_snippet"):
                raise ValueError("unsupported reference field")
            text = page[ref["field"]]
            if not 0 <= start < end <= len(text):
                raise ValueError("reference span out of range")
            if page["page_url"] != ref["source_url"] or text[start:end] != ref["quote"]:
                raise ValueError("reference differs from pinned source")
            references += 1
    return {
        "status": "review_export_validated",
        "records": len(rows),
        "reviewer": export["reviewer"],
        "decisions": dict(Counter(r["status"] for r in rows)),
        "verified_source_spans": references,
        "export_sha256": sha256_file(export_path),
        "query_ids": ids,
        "complete_evidence_labels_available": False,
        "evaluation_gate_complete": False,
        "scope": "Human decisions over AI-assisted development drafts; no held-out quality claim.",
    }


def import_review(export_path: Path, dataset_config: dict, root: Path, output: Path) -> dict:
    result = validate_review_export(export_path, dataset_config, root)
    output.mkdir(parents=True, exist_ok=False)
    (output / "original-export.json").write_bytes(export_path.read_bytes())
    if sha256_file(output / "original-export.json") != result["export_sha256"]:
        raise ValueError("export changed during import")
    write_json(output / "validation.json", result)
    return result
