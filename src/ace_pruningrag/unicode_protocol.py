"""Fixed identity and bounds for the separately versioned Unicode GPU control."""

from .artifacts import read_json, sha256_file


def validate_protocol(root, config):
    original = read_json(root / "configs/constrained_extraction.json")
    expected = {
        **original,
        "scope": (
            "Versioned Unicode boundary correction with frozen blinded tasks and generator "
            "controls; no semantic acceptance"
        ),
        "protocol_id": "unicode_combining_marks_v2",
        "span_policy_module": "ace_pruningrag.unicode_claims",
        "span_policy_sha256": sha256_file(root / "src/ace_pruningrag/unicode_claims.py"),
    }
    if config != expected:
        raise ValueError("Unicode protocol identity, bounds or policy hash differs")
