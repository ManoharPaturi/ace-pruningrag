"""Retain post-hoc synthetic demonstrations of v1 prompt/grammar/validator gaps."""

import argparse
import copy
import json
from pathlib import Path

from ace_pruningrag.artifacts import sha256_file, write_json
from ace_pruningrag.query_requirements import CLAUSE_FIELDS, character_parser, messages, validate


def accepts(task, proposal):
    parser = character_parser(task)
    raw = json.dumps(proposal, ensure_ascii=False, separators=(",", ":"))
    for char in raw:
        if char not in parser.get_allowed_characters():
            return False
        parser = parser.add_character(char)
    return parser.can_end()


def variable(identifier, kind, role, cue, constant=None):
    return {
        "id": identifier,
        "kind": kind,
        "role": role,
        "value_type": "entity",
        "cue": cue,
        "constant": constant,
    }


def clause(text, **values):
    return {k: text if k == "text" else values.get(k) for k in CLAUSE_FIELDS}


def diagnostic(root):
    task = {
        "kind": "query",
        "text": "Who owns the company that publishes a journal?",
        "query_time": "2024",
    }
    p = {
        "status": "proposed_complete",
        "composition": "all",
        "cardinality": None,
        "variables": [
            variable("v0", "answer", "subject", "Who"),
            variable("v1", "latent", "subject", "company"),
            variable("v2", "context", "object", "journal", "journal"),
        ],
        "clauses": [
            clause(
                "company that publishes a journal",
                subject={"variable": "v1"},
                relation="publishes",
                object={"variable": "v2"},
            ),
            clause(
                "Who owns the company",
                subject={"variable": "v0"},
                relation="owns",
                object={"variable": "v1"},
            ),
        ],
        "operation": {"kind": "select", "cue": "Who", "operands": ["v1"], "result": "v0"},
    }
    chain = validate(task, json.dumps(p))
    unknown = copy.deepcopy(p)
    unknown["variables"][1]["role"] = "unknown"
    unknown_result = validate(task, json.dumps(unknown))
    nullable = copy.deepcopy(unknown)
    nullable["operation"].update(cue=None, result=None)
    nullable_result = validate(task, json.dumps(nullable))
    empty = copy.deepcopy(unknown)
    empty["clauses"] = [clause(task["text"])]
    empty["operation"] = {"kind": "unknown", "cue": None, "operands": [], "result": None}
    empty_result = validate(task, json.dumps(empty))
    if (
        chain["issues"] != ["inconsistent_variable_role_clause_1_object"]
        or unknown_result["status"] != "bound_requirement_proposal"
        or nullable_result["issues"] != ["operation_missing_cue", "operation_missing_result"]
        or empty_result["status"] != "bound_requirement_proposal"
        or not all(accepts(task, x) for x in (p, unknown, nullable, empty))
    ):
        raise ValueError("frozen v1 synthetic contract demonstration differs")
    return {
        "scope": (
            "Post-hoc synthetic engineering diagnosis; "
            "not a new neural result or altered control score"
        ),
        "policy_sha256": sha256_file(root / "src/ace_pruningrag/query_requirements.py"),
        "prompt_says_nullable_operation_fields": (
            "cue is an exact TEXT span or null" in messages(task)[0]["content"]
            and "answer/latent variable ID or null" in messages(task)[0]["content"]
        ),
        "fixed_variable_role_rejects_two_edge_entity_chain": chain["issues"],
        "same_chain_with_unknown_role_status": unknown_result["status"],
        "grammar_accepts_known_operation_with_null_cue_result": accepts(task, nullable),
        "validator_rejects_known_operation_null_fields": nullable_result["issues"],
        "unlinked_variables_and_all_null_clause_pass_structural_status": empty_result["status"],
        "demonstrations": {
            "task": task,
            "entity_chain": p,
            "nullable_operation": nullable,
            "empty_clause": empty,
        },
        "actual_model_calls": 0,
        "semantic_requirements_verified": False,
        "answer_acceptance_enabled": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    write_json(args.output, diagnostic(Path.cwd()))
