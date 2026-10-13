"""Separately pinned query-only logical extraction protocol."""

from .artifacts import read_json, sha256_file
from .claim_extraction import extraction_tasks
from .query_requirements import MAX_CLAUSES, MAX_VARIABLES


def requirement_tasks(rows):
    return [t for t in extraction_tasks(rows) if t["kind"] == "query"]


def validate_protocol(root, config):
    expected = {
        **read_json(root / "configs/inventory_extraction.json"),
        "scope": "Blinded query-only unknown-answer requirement diagnostic; no semantic acceptance",
        "max_tasks": 50,
        "protocol_id": "query_requirements_v1",
        "span_policy_module": "ace_pruningrag.query_requirements",
        "span_policy_sha256": sha256_file(root / "src/ace_pruningrag/query_requirements.py"),
        "max_variables": 8,
        "max_clauses": 12,
    }
    expected.pop("max_frames")
    if config != expected or MAX_VARIABLES != 8 or MAX_CLAUSES != 12:
        raise ValueError("requirements prompt/policy identity or bounded configuration differs")
