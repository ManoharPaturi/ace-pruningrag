"""Explicit changed-prompt and expanded-output inventory extraction protocol."""

from .artifacts import read_json, sha256_file
from .claim_inventory import MAX_FRAMES


def validate_protocol(root, config):
    expected = {
        **read_json(root / "configs/unicode_extraction.json"),
        "scope": "Blinded plural claim/requirement inventory diagnostic; no semantic acceptance",
        "protocol_id": "inventory_frames_v1",
        "span_policy_module": "ace_pruningrag.claim_inventory",
        "span_policy_sha256": sha256_file(root / "src/ace_pruningrag/claim_inventory.py"),
        "max_output_tokens": 2048,
        "max_input_and_output_tokens": 4096,
        "max_frames": 12,
    }
    if config != expected or MAX_FRAMES != config["max_frames"]:
        raise ValueError("inventory prompt/policy identity or bounded configuration differs")
