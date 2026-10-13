from pathlib import Path

import pytest

from ace_pruningrag.artifacts import read_json
from ace_pruningrag.query_graph_protocol import validate_protocol

ROOT = Path(__file__).resolve().parents[1]


def test_graph_factor_pins_contract_and_preserves_model_decoding_and_budget():
    config = read_json(ROOT / "configs/query_graph_v2.json")
    validate_protocol(ROOT, config)
    control = read_json(ROOT / "configs/query_requirements_3b.json")
    for key in (
        "generator_config",
        "generator_config_sha256",
        "decoding_config",
        "decoding_config_sha256",
        "batch_size",
        "seed",
        "dtype",
        "max_output_tokens",
        "max_input_and_output_tokens",
    ):
        assert config[key] == control[key]
    for key, value in (
        ("max_operations", 9),
        ("allow_answer_acceptance", True),
        ("max_output_tokens", 2049),
        ("contract_sha256", {name: "0" * 64 for name in config["contract_sha256"]}),
    ):
        with pytest.raises(ValueError, match="query graph"):
            validate_protocol(ROOT, {**config, key: value})
