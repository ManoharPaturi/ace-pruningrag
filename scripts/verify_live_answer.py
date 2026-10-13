"""Independently reconstruct one live GPU result without using gold labels."""

import argparse
import ast
import base64
import hashlib
import json
import math
import zlib
from pathlib import Path

from transformers import AutoTokenizer

from ace_pruningrag.answer_checks import check_answer_form
from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.dataset import iter_records, verify_dataset
from ace_pruningrag.live_generation import prepare_live


def verify(root, bundle_dir, run):
    tree = ast.parse((bundle_dir / "bootstrap.py").read_text())
    assignment = next(
        n
        for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "PAYLOAD" for t in n.targets)
    )
    bundle = json.loads(zlib.decompress(base64.b64decode(ast.literal_eval(assignment.value))))
    hashes = read_json(bundle_dir / "bundle-manifest.json")
    if bundle["sha256"] != hashes or read_json(run / "bundle_manifest.json") != hashes:
        raise ValueError("live submitted/output source manifests differ")
    for name, content in bundle["files"].items():
        if hashlib.sha256(content.encode()).hexdigest() != hashes[name]:
            raise ValueError("live submitted file content differs")
        if name != "configs/live_request.json" and sha256_file(root / name) != hashes[name]:
            raise ValueError(f"current source differs from live submitted version: {name}")
    request = json.loads(bundle["files"]["configs/live_request.json"])
    config = read_json(root / "configs/generated_pilot.json")
    completion = read_json(run / "completion.json")
    result = read_json(run / "result.json")
    isolation = read_json(run / "environment_isolation.json")
    if (
        isolation.get("base_preserved") is not True
        or isolation["base_before"] != isolation["base_after"]
    ):
        raise ValueError("live base environment isolation differs")
    versions = {
        "transformers": "4.57.3",
        "huggingface_hub": "0.36.0",
        "tokenizers": "0.22.1",
        "safetensors": "0.6.2",
        "sentencepiece": "0.2.1",
    }
    if result.get("dependency_versions") != versions:
        raise ValueError("live inference dependency versions differ")
    if completion != {
        "status": "one_live_answer_generated",
        "request_id": request["request_id"],
        "actual_llm_calls": 1,
        "result_sha256": sha256_file(run / "result.json"),
    }:
        raise ValueError("live completion differs or result is changed")
    dataset = verify_dataset(read_json(root / config["dataset_config"]), root)
    q = next(
        r.inference_input()
        for r in iter_records(dataset)
        if r.interaction_id == request["interaction_id"]
    )
    tokenizer = AutoTokenizer.from_pretrained(
        root / config["generator"]["directory"],
        local_files_only=True,
        trust_remote_code=False,
    )
    p = prepare_live(
        q,
        config,
        lambda m: tokenizer.apply_chat_template(m, tokenize=True, add_generation_prompt=True),
    )
    expected = {
        "mode": "new_gpu_generation",
        "request_id": request["request_id"],
        "interaction_id": q.interaction_id,
        "query": q.query,
        "query_time": q.query_time,
        "policy": "fixed_web",
        "selected": p["evidence"],
        "input_tokens": len(p["input_ids"]),
        "maximum_reserved_tokens": len(p["input_ids"]) + 96,
        "actual_llm_calls": 1,
        "actual_source_calls": p["source_calls"],
        "dataset_sha256": sha256_file(dataset),
        "generator": config["generator"],
        "generator_config_sha256": sha256_file(root / "configs/generated_pilot.json"),
        "prompt_sha256": hashlib.sha256(
            json.dumps(p["messages"], ensure_ascii=False).encode()
        ).hexdigest(),
    }
    if any(result.get(k) != v for k, v in expected.items()):
        raise ValueError("live result differs from reconstructed request/provenance")
    ids = result["output_ids"]
    if not ids or any(type(i) is not int or i < 0 for i in ids) or len(ids) > 96:
        raise ValueError("live output IDs invalid")
    if (
        result["output_tokens"] != len(ids)
        or result["prediction"] != tokenizer.decode(ids, skip_special_tokens=True).strip()
    ):
        raise ValueError("live decoded output differs")
    if result["maximum_reserved_tokens"] > 2048 or result["runtime"]["dtype"] != "float32":
        raise ValueError("live runtime or token contract differs")
    if not math.isfinite(result["generation_seconds"]) or result["generation_seconds"] < 0:
        raise ValueError("live timing invalid")
    if any(k in result for k in ("evaluation", "answer", "gold_answer", "domain", "split")):
        raise ValueError("evaluation labels in live result")
    if result["answer_form_checks"] != check_answer_form(
        q.query, result["prediction"], [e["evidence_id"] for e in p["evidence"]]
    ):
        raise ValueError("live answer-form diagnostics differ")
    return {
        "status": "one_live_gpu_result_reconstructed",
        "request_id": request["request_id"],
        "result_sha256": sha256_file(run / "result.json"),
        "actual_llm_calls": 1,
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "maximum_reserved_tokens": result["maximum_reserved_tokens"],
        "human_validated": False,
        "claim_support_verified": False,
        "scope": "Live worker execution/provenance, not full demo or scientific completion",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    write_json(args.output, verify(Path.cwd(), args.bundle, args.run))
