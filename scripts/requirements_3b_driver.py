"""Bounded batched GPU extraction, blinded to model answers and evaluation labels."""

import argparse
import importlib.metadata
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--overlay", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    sys.path.insert(0, str(args.overlay))
    sys.path.insert(0, str(args.root / "src"))
    os.environ["USE_TF"] = "0"
    os.environ["USE_FLAX"] = "0"
    import torch
    from lmformatenforcer.integrations.transformers import (
        build_token_enforcer_tokenizer_data,
        build_transformers_prefix_allowed_tokens_fn,
    )
    from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig, LogitsProcessor

    from ace_pruningrag.artifacts import read_json, sha256_file, write_json
    from ace_pruningrag.claim_extraction import digest
    from ace_pruningrag.query_requirements import (
        character_parser,
    )
    from ace_pruningrag.query_requirements import (
        messages as extraction_messages,
    )
    from ace_pruningrag.query_requirements import (
        validate as validate_constrained,
    )
    from ace_pruningrag.unicode_claims import permitted_spans

    versions = {
        "transformers": "4.57.3",
        "huggingface_hub": "0.36.0",
        "tokenizers": "0.22.1",
        "safetensors": "0.6.2",
        "sentencepiece": "0.2.1",
    }
    if {k: importlib.metadata.version(k) for k in versions} != versions:
        raise ValueError("extraction isolated dependency versions differ")
    config = read_json(args.root / "configs/query_requirements_3b.json")
    from ace_pruningrag.requirements_3b_protocol import validate_protocol

    validate_protocol(args.root, config)
    expected_constraints = config["constraints_dependencies"]
    if {k: importlib.metadata.version(k) for k in expected_constraints} != expected_constraints:
        raise ValueError("constrained dependency versions differ")
    base = read_json(args.root / config["generator_config"])
    tasks = read_json(args.root / "configs/constrained_tasks.json")["tasks"]
    if (
        len(tasks) > config["max_tasks"]
        or config["max_output_tokens"] != 2048
        or config["batch_size"] != 4
        or config["max_input_and_output_tokens"] != 4096
        or config["allow_answer_acceptance"] is not False
        or config["dtype"] != "float32"
        or any(t["kind"] != "query" for t in tasks)
        or not torch.cuda.is_available()
    ):
        raise ValueError("extraction bounded protocol differs")
    torch.manual_seed(config["seed"])
    torch.cuda.manual_seed_all(config["seed"])
    torch.backends.cudnn.benchmark = False
    directory = args.root / base["generator"]["directory"]
    tokenizer = AutoTokenizer.from_pretrained(
        directory, local_files_only=True, trust_remote_code=False
    )
    encoded = [
        tokenizer.apply_chat_template(
            extraction_messages(t), tokenize=True, add_generation_prompt=True
        )
        for t in tasks
    ]
    started = time.perf_counter()
    model = (
        AutoModelForCausalLM.from_pretrained(
            directory,
            local_files_only=True,
            trust_remote_code=False,
            torch_dtype=torch.float32,
            attn_implementation="eager",
        )
        .to("cuda:0")
        .eval()
    )
    model.generation_config = GenerationConfig.from_dict(
        read_json(args.root / config["decoding_config"])
    )
    loading = time.perf_counter() - started
    if not all(bool(torch.isfinite(p).all().item()) for p in model.parameters()):
        raise ValueError("nonfinite extraction model parameters")

    class FiniteScores(LogitsProcessor):
        def __call__(self, input_ids, scores):
            if (
                torch.isnan(scores).any()
                or torch.isposinf(scores).any()
                or not torch.isfinite(scores).any(dim=-1).all()
            ):
                raise ValueError("nonfinite extraction generation scores")
            return scores

    eos = model.generation_config.eos_token_id
    eos_set = set(eos if isinstance(eos, list) else [eos])
    tokenizer_data = build_token_enforcer_tokenizer_data(tokenizer)
    tokenizer_data.eos_token_id = sorted(eos_set)
    span_counts = [len(permitted_spans(task["text"])) for task in tasks]
    eligible, results = [], [None] * len(tasks)
    for i, ids in enumerate(encoded):
        if len(ids) + 2048 > 4096:
            results[i] = {
                "task_sha256": tasks[i]["task_sha256"],
                "input_tokens": len(ids),
                "input_ids_sha256": digest(ids),
                "status": "over_budget_unextracted",
                "actual_extraction_sequences": 0,
            }
        else:
            eligible.append(i)
    invocations, generation, padded = 0, 0.0, 0
    args.output.mkdir(parents=True, exist_ok=True)
    progress = args.output / "progress.jsonl"
    with progress.open("x") as stream:
        for offset in range(0, len(eligible), 4):
            indices = eligible[offset : offset + 4]
            width = max(len(encoded[i]) for i in indices)
            padded += width * len(indices)
            inputs = torch.tensor(
                [
                    [tokenizer.eos_token_id] * (width - len(encoded[i])) + encoded[i]
                    for i in indices
                ],
                device="cuda:0",
            )
            mask = torch.tensor(
                [[0] * (width - len(encoded[i])) + [1] * len(encoded[i]) for i in indices],
                device="cuda:0",
            )
            filters = [
                build_transformers_prefix_allowed_tokens_fn(
                    tokenizer_data, character_parser(tasks[i])
                )
                for i in indices
            ]

            def allowed(batch_id, sent, filters=filters):
                return filters[batch_id](0, sent)

            torch.cuda.synchronize()
            began = time.perf_counter()
            with torch.inference_mode():
                generated = model.generate(
                    input_ids=inputs,
                    attention_mask=mask,
                    max_new_tokens=2048,
                    do_sample=False,
                    num_beams=1,
                    temperature=None,
                    top_p=None,
                    top_k=None,
                    logits_processor=[FiniteScores()],
                    pad_token_id=tokenizer.eos_token_id,
                    prefix_allowed_tokens_fn=allowed,
                )
            torch.cuda.synchronize()
            generation += time.perf_counter() - began
            invocations += 1
            for i, output in zip(indices, generated[:, width:].cpu().tolist(), strict=True):
                # Count the first terminator; subsequent batch padding is not generated content.
                stop = next(
                    (j + 1 for j, token in enumerate(output) if token in eos_set), len(output)
                )
                output = output[:stop]
                raw = tokenizer.decode(output, skip_special_tokens=True).strip()
                result = {
                    "task_sha256": tasks[i]["task_sha256"],
                    "kind": tasks[i]["kind"],
                    "input_tokens": len(encoded[i]),
                    "input_ids_sha256": digest(encoded[i]),
                    "output_ids": output,
                    "output_tokens": len(output),
                    "raw_proposal": raw,
                    "messages_sha256": digest(extraction_messages(tasks[i])),
                    "validation": validate_constrained(tasks[i], raw),
                    "permitted_span_count": span_counts[i],
                    "hit_output_cap_without_eos": len(output) == 2048 and output[-1] not in eos_set,
                    "actual_extraction_sequences": 1,
                }
                results[i] = result
                stream.write(json.dumps(result) + "\n")
            stream.flush()
            print(
                f"Extraction sequences {min(offset + 4, len(eligible))}/{len(eligible)}", flush=True
            )
    trace = args.output / "extractions.jsonl"
    with trace.open("x") as stream:
        for result in results:
            stream.write(json.dumps(result) + "\n")
    write_json(
        args.output / "completion.json",
        {
            "status": "bounded_requirements_extraction_complete",
            "protocol_id": config["protocol_id"],
            "extractor_repository": base["generator"]["repository"],
            "extractor_revision": base["generator"]["revision"],
            "decoding_defaults_sha256": sha256_file(args.root / config["decoding_config"]),
            "span_policy_sha256": config["span_policy_sha256"],
            "tasks": len(tasks),
            "extraction_sequences": len(eligible),
            "generate_invocations": invocations,
            "unextracted": len(tasks) - len(eligible),
            "input_tokens": sum(len(encoded[i]) for i in eligible),
            "padded_input_tokens": padded,
            "output_tokens": sum(r.get("output_tokens", 0) for r in results),
            "maximum_reserved_request_tokens": max(
                (len(encoded[i]) + 2048 for i in eligible), default=0
            ),
            "generation_seconds": generation,
            "model_loading_seconds": loading,
            "trace_sha256": sha256_file(trace),
            "tasks_sha256": sha256_file(args.root / "configs/constrained_tasks.json"),
            "validation_counts": dict(
                Counter(r.get("validation", {}).get("status", r.get("status")) for r in results)
            ),
            "actual_new_answer_generation_calls": 0,
            "answer_acceptance_enabled": False,
            "semantic_requirements_verification": False,
            "runtime": {
                "torch": torch.__version__,
                "cuda": torch.version.cuda,
                "gpu": torch.cuda.get_device_name(0),
                "dtype": "float32",
            },
            "dependency_versions": versions,
            "constraint_dependency_versions": expected_constraints,
            "format_enforcement": "ordered_JSON_bounded_requirement_reference_trie",
            "eos_token_ids": sorted(eos_set),
            "scope": config["scope"],
        },
    )


if __name__ == "__main__":
    main()
