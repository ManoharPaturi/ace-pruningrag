"""One bounded independent NLI classifier run over exact frozen source/answer pairs."""

import argparse
import importlib.metadata
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.overlay))
    sys.path.insert(0, str(args.root / "src"))
    os.environ["USE_TF"] = "0"
    os.environ["USE_FLAX"] = "0"
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    from ace_pruningrag.artifacts import read_json, sha256_file, write_json
    from ace_pruningrag.nli_diagnostic import diagnostic_record

    config = read_json(args.root / "configs/nli_diagnostic.json")
    pairs = read_json(args.root / "configs/nli_pairs.json")["pairs"]
    if (
        len(pairs) > config["max_pairs"]
        or config["batch_size"] != 16
        or config["max_pair_tokens"] != 512
    ):
        raise ValueError("NLI bounded protocol differs")
    if not torch.cuda.is_available() or config["dtype"] != "float32":
        raise ValueError("NLI diagnostic requires actual float32 CUDA")
    if importlib.metadata.version("transformers") != "4.57.3":
        raise ValueError("NLI inference version differs")
    torch.manual_seed(config["seed"])
    directory = args.root / "data/models/nli"
    tokenizer = AutoTokenizer.from_pretrained(
        directory, local_files_only=True, trust_remote_code=False
    )
    started = time.perf_counter()
    model = (
        AutoModelForSequenceClassification.from_pretrained(
            directory,
            local_files_only=True,
            trust_remote_code=False,
            torch_dtype=torch.float32,
        )
        .to("cuda:0")
        .eval()
    )
    if [model.config.id2label[i] for i in range(3)] != config["labels"]:
        raise ValueError("NLI label mapping differs")
    if not all(bool(torch.isfinite(p).all().item()) for p in model.parameters()):
        raise ValueError("nonfinite classifier parameters")
    loading = time.perf_counter() - started
    encoded = [tokenizer(p["premise"], p["hypothesis"], truncation=False) for p in pairs]
    results = [None] * len(pairs)
    eligible = []
    for i, item in enumerate(encoded):
        count = len(item["input_ids"])
        if count > 512:
            results[i] = diagnostic_record(pairs[i], count)
        else:
            eligible.append(i)
    calls, scoring = 0, 0.0
    for offset in range(0, len(eligible), 16):
        indices = eligible[offset : offset + 16]
        features = tokenizer.pad([encoded[i] for i in indices], padding=True, return_tensors="pt")
        features = {k: v.to("cuda:0") for k, v in features.items()}
        torch.cuda.synchronize()
        began = time.perf_counter()
        with torch.inference_mode():
            logits = model(**features).logits
        torch.cuda.synchronize()
        scoring += time.perf_counter() - began
        if not bool(torch.isfinite(logits).all().item()):
            raise ValueError("nonfinite classifier logits")
        calls += 1
        for i, scores in zip(indices, logits.cpu().tolist(), strict=True):
            results[i] = diagnostic_record(pairs[i], len(encoded[i]["input_ids"]), scores)
    args.output.mkdir(parents=True, exist_ok=True)
    trace = args.output / "nli.jsonl"
    with trace.open("x") as stream:
        for result in results:
            stream.write(json.dumps(result) + "\n")
    write_json(
        args.output / "completion.json",
        {
            "status": "bounded_nli_diagnostic_complete",
            "comparisons": len(pairs),
            "scored_pairs": len(eligible),
            "unscored_pairs": len(pairs) - len(eligible),
            "classifier_forward_calls": calls,
            "actual_llm_generation_calls": 0,
            "input_pair_tokens": sum(len(encoded[i]["input_ids"]) for i in eligible),
            "model_loading_seconds": loading,
            "classifier_seconds": scoring,
            "model_labels": dict(Counter(r.get("model_label", "unscored") for r in results)),
            "trace_sha256": sha256_file(trace),
            "pairs_sha256": sha256_file(args.root / "configs/nli_pairs.json"),
            "runtime": {
                "torch": torch.__version__,
                "cuda": torch.version.cuda,
                "gpu": torch.cuda.get_device_name(0),
                "dtype": "float32",
            },
            "calibrated": False,
            "factual_accuracy": None,
            "answer_completeness": None,
            "scope": config["scope"],
        },
    )


if __name__ == "__main__":
    main()
