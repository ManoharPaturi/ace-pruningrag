"""Pinned extractor model variant with the frozen v1 query contract and decoding defaults."""

from .artifacts import read_json, sha256_file
from .requirements_protocol import validate_protocol as validate_control

MODEL_REVISION = "aa8e72537993ba99e69dfaafa59ed015b17504d1"
MODEL_CONFIG_SHA256 = "d207e19a961f70cdc28e1aae6de49239057daf56c0537ff07f37c61625c1792e"
DECODING_CONFIG_SHA256 = "e558847a8b4402616f1273797b015104dc266fe4b520056fca88823ba8f8ebe6"


def validate_protocol(root, config):
    control = read_json(root / "configs/query_requirements.json")
    validate_control(root, control)
    expected = {
        **control,
        "scope": (
            "Blinded query-only requirement extraction; 3B model variant with frozen v1 "
            "prompts/grammar/decoding"
        ),
        "protocol_id": "query_requirements_model_3b_v1",
        "generator_config": "configs/requirements_extractor_3b.json",
        "generator_config_sha256": MODEL_CONFIG_SHA256,
        "decoding_config": "configs/requirements_control_decoding.json",
        "decoding_config_sha256": DECODING_CONFIG_SHA256,
    }
    if (
        config != expected
        or sha256_file(root / expected["generator_config"]) != MODEL_CONFIG_SHA256
        or sha256_file(root / expected["decoding_config"]) != DECODING_CONFIG_SHA256
    ):
        raise ValueError("3B model-variant protocol, pinned assets or control decoding differs")
