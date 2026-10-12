"""Fresh isolated GPU process: actual generation for explicit cohort/selector pairs."""

import argparse
import importlib.metadata
import json
import os
import sys
import time
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
    from transformers import AutoModelForCausalLM, AutoTokenizer, LogitsProcessor

    from ace_pruningrag.artifacts import sha256_file, write_json
    from ace_pruningrag.cohort import METHODS, load_cohort, prepare_selectors, source_hashes
    from ace_pruningrag.generation import evaluate_answer

    expected = {
        "transformers": "4.57.3",
        "huggingface_hub": "0.36.0",
        "tokenizers": "0.22.1",
        "safetensors": "0.6.2",
        "sentencepiece": "0.2.1",
    }
    versions = {k: importlib.metadata.version(k) for k in expected}
    if versions != expected or not torch.cuda.is_available():
        raise ValueError("pinned isolated inference versions and GPU required")
    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    protocol, config, records = load_cohort(args.root, output / "cohort")
    if config["generator"]["dtype"] != "float32":
        raise ValueError("float32 model required")
    torch.manual_seed(protocol["seed"])
    torch.cuda.manual_seed_all(protocol["seed"])
    torch.backends.cudnn.benchmark = False
    started = time.perf_counter()
    model_dir = args.root / config["generator"]["directory"]
    tokenizer = AutoTokenizer.from_pretrained(
        model_dir, local_files_only=True, trust_remote_code=False
    )
    model = (
        AutoModelForCausalLM.from_pretrained(
            model_dir,
            local_files_only=True,
            trust_remote_code=False,
            torch_dtype=torch.float32,
            attn_implementation="eager",
        )
        .to("cuda:0")
        .eval()
    )
    if not all(bool(torch.isfinite(p).all().item()) for p in model.parameters()):
        raise ValueError("nonfinite parameters")
    loading_seconds = time.perf_counter() - started

    class Guard(LogitsProcessor):
        def __call__(self, input_ids, scores):
            if (
                torch.isnan(scores).any()
                or torch.isposinf(scores).any()
                or not torch.isfinite(scores).any(dim=-1).all()
            ):
                raise ValueError("nonfinite or entirely masked generation scores")
            return scores

    rows, query_costs = [], []
    with (output / "predictions.jsonl").open("x") as stream:
        for index, record in enumerate(records):
            query = record.inference_input()
            prepared, costs = prepare_selectors(
                query,
                config,
                lambda m: tokenizer.apply_chat_template(
                    m, tokenize=True, add_generation_prompt=True
                ),
            )
            query_costs.append(dict(costs, interaction_id=query.interaction_id))
            order = METHODS[index % 5 :] + METHODS[: index % 5]
            for method in order:
                if len(rows) >= protocol["max_llm_calls"]:
                    raise ValueError("stop before exceeding generation-call cap")
                request = prepared[method]
                inputs = torch.tensor([request["input_ids"]], device="cuda:0")
                torch.cuda.synchronize()
                started = time.perf_counter()
                with torch.inference_mode():
                    result = model.generate(
                        input_ids=inputs,
                        attention_mask=torch.ones_like(inputs),
                        logits_processor=[Guard()],
                        do_sample=False,
                        num_beams=1,
                        max_new_tokens=config["max_new_tokens"],
                        pad_token_id=tokenizer.eos_token_id,
                        temperature=None,
                        top_p=None,
                        top_k=None,
                    )
                torch.cuda.synchronize()
                seconds = time.perf_counter() - started
                tail = result[0, inputs.shape[1] :].tolist()
                if (
                    len(tail) > config["max_new_tokens"]
                    or len(request["input_ids"]) + len(tail) > config["total_tokens"]
                ):
                    raise ValueError("executed token budget exceeded")
                prediction = tokenizer.decode(tail, skip_special_tokens=True).strip()
                row = {k: v for k, v in request.items() if k not in ("messages", "input_ids")}
                row.update(
                    interaction_id=query.interaction_id,
                    query=query.query,
                    query_time=query.query_time,
                    policy=method,
                    execution_order=list(order),
                    prediction=prediction,
                    input_tokens=len(request["input_ids"]),
                    output_tokens=len(tail),
                    output_ids=tail,
                    actual_llm_calls=1,
                    generation_seconds=seconds,
                    evaluation=evaluate_answer(prediction, record.answers),
                )
                rows.append(row)
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
            print(f"Generated query {index + 1}/50, five selectors", flush=True)
    runtime = dict(
        versions,
        torch=torch.__version__,
        cuda=torch.version.cuda,
        gpus=[torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
    )
    summary = {
        "status": "exploratory_cohort_generation_completed",
        "queries": len(records),
        "actual_llm_calls": len(rows),
        "actual_judge_calls": 0,
        "actual_finance_calls": 0,
        "shared_candidate_retrievals": len(query_costs),
        "input_tokens": sum(r["input_tokens"] for r in rows),
        "output_tokens": sum(r["output_tokens"] for r in rows),
        "maximum_reserved_tokens": max(r["input_tokens"] + config["max_new_tokens"] for r in rows),
        "model_loading_seconds": loading_seconds,
        "generation_seconds": sum(r["generation_seconds"] for r in rows),
        "runtime": runtime,
        "numerical_checks": {
            "dtype": "float32",
            "parameters_finite": True,
            "per_step_scores_guarded": True,
        },
        "human_semantic_accuracy": None,
        "evidence_completeness": None,
        "publication_results": False,
        "per_method": {
            m: {
                "answers": sum(r["policy"] == m for r in rows),
                "literal_matches": sum(
                    r["evaluation"]["exact_agreement"] for r in rows if r["policy"] == m
                ),
                "abstentions": sum(r["evaluation"]["abstained"] for r in rows if r["policy"] == m),
            }
            for m in METHODS
        },
    }
    write_json(output / "summary.json", summary)
    write_json(output / "retrieval_costs.json", query_costs)
    write_json(
        output / "manifest.json",
        {
            "protocol": protocol,
            "generator_config": config,
            "protocol_sha256": sha256_file(args.root / "configs/cohort_evaluation.json"),
            "trace_sha256": sha256_file(output / "predictions.jsonl"),
            "retrieval_costs_sha256": sha256_file(output / "retrieval_costs.json"),
            "source_sha256": source_hashes(args.root),
            "runtime": runtime,
        },
    )
    write_json(
        output.parent / "completion.json",
        {"status": summary["status"], "queries": len(records), "actual_llm_calls": len(rows)},
    )


if __name__ == "__main__":
    main()
