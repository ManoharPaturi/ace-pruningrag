"""Pin the typed graph factor independently of the previous model-only variant."""

from .artifacts import read_json, sha256_file
from .query_graph import MAX_CLAUSES, MAX_OPERATIONS, MAX_VARIABLES
from .requirements_3b_protocol import validate_protocol as validate_control


def validate_protocol(root, config):
    control = read_json(root / "configs/query_requirements_3b.json")
    validate_control(root, control)
    expected = {
        **control,
        "scope": (
            "Blinded typed query graph v2; changed prompt/schema/grammar with pinned 3B "
            "and control decoding"
        ),
        "protocol_id": "query_graph_v2",
        "max_operations": 8,
        "contract_sha256": {
            name: sha256_file(root / name)
            for name in (
                "src/ace_pruningrag/query_graph.py",
                "src/ace_pruningrag/query_graph_decoder.py",
                "src/ace_pruningrag/query_graph_prompt.py",
            )
        },
    }
    expected.pop("span_policy_module")
    expected.pop("span_policy_sha256")
    if config != expected or (MAX_VARIABLES, MAX_CLAUSES, MAX_OPERATIONS) != (8, 12, 8):
        raise ValueError("query graph contract identity or bounded protocol differs")
