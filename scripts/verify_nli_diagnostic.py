"""Reconstruct NLI input bindings, token caps and reported labels, not model accuracy."""

import argparse
import ast
import base64
import hashlib
import json
import math
import zlib
from collections import Counter
from pathlib import Path

from transformers import AutoTokenizer

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.nli_diagnostic import answer_source_pairs, diagnostic_record


def verify(root, bundle_dir, run, source_trace):
    tree = ast.parse((bundle_dir / "bootstrap.py").read_text())
    assignment = next(
        n
        for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "PAYLOAD" for t in n.targets)
    )
    payload = json.loads(zlib.decompress(base64.b64decode(ast.literal_eval(assignment.value))))
    hashes = read_json(bundle_dir / "bundle-manifest.json")
    if payload["sha256"] != hashes or read_json(run / "bundle_manifest.json") != hashes:
        raise ValueError("NLI bundle manifests differ")
    for name, content in payload["files"].items():
        if hashlib.sha256(content.encode()).hexdigest() != hashes[name]:
            raise ValueError("NLI bundle content differs")
        if name != "configs/nli_pairs.json" and sha256_file(root / name) != hashes[name]:
            raise ValueError(f"NLI submitted source differs: {name}")
    config = read_json(root / "configs/nli_diagnostic.json")
    inputs = json.loads(payload["files"]["configs/nli_pairs.json"])
    if inputs["source_trace_sha256"] != sha256_file(source_trace):
        raise ValueError("NLI source answer trace differs")
    source = [json.loads(x) for x in source_trace.read_text().splitlines()]
    pairs = answer_source_pairs(source, config["max_pairs"])
    if inputs["pairs"] != pairs:
        raise ValueError("NLI pairs differ from actual predictions/evidence")
    tokenizer = AutoTokenizer.from_pretrained(
        root / "data/models/nli", local_files_only=True, trust_remote_code=False
    )
    records = [json.loads(x) for x in (run / "nli.jsonl").read_text().splitlines()]
    if len(records) != len(pairs):
        raise ValueError("NLI record coverage differs")
    eligible = []
    for pair, record in zip(pairs, records, strict=True):
        n = len(tokenizer(pair["premise"], pair["hypothesis"], truncation=False)["input_ids"])
        if record != diagnostic_record(pair, n, record.get("logits"), config["max_pair_tokens"]):
            raise ValueError("NLI binding/tokens/label differs")
        if n <= 512:
            eligible.append(n)
    summary = read_json(run / "completion.json")
    expected = {
        "comparisons": len(pairs),
        "scored_pairs": len(eligible),
        "unscored_pairs": len(pairs) - len(eligible),
        "classifier_forward_calls": math.ceil(len(eligible) / 16),
        "actual_llm_generation_calls": 0,
        "input_pair_tokens": sum(eligible),
        "trace_sha256": sha256_file(run / "nli.jsonl"),
        "pairs_sha256": hashes["configs/nli_pairs.json"],
        "model_labels": dict(Counter(r.get("model_label", "unscored") for r in records)),
    }
    if any(summary.get(k) != v for k, v in expected.items()):
        raise ValueError("NLI cost or trace summary differs")
    isolation = read_json(run / "environment_isolation.json")
    if (
        isolation["base_preserved"] is not True
        or isolation["base_before"] != isolation["base_after"]
    ):
        raise ValueError("NLI dependency isolation differs")
    padded = sum(
        max(eligible[i : i + 16]) * len(eligible[i : i + 16]) for i in range(0, len(eligible), 16)
    )
    return {
        **expected,
        "status": "nli_bindings_tokens_and_labels_reconstructed",
        "padded_classifier_input_tokens": padded,
        "model_revision": config["revision"],
        "calibrated": False,
        "factual_accuracy": None,
        "answer_completeness": None,
        "scope": "Post-hoc unframed text diagnostics; logits were not independently recomputed",
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--source-trace", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)
    write_json(a.output, verify(Path.cwd(), a.bundle, a.run, a.source_trace))
