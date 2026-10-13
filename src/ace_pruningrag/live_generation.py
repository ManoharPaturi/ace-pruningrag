"""One actual GPU answer on pinned query inputs, without gold scoring or trace mutation."""

import hashlib
import json
import math
import time

from .answer_checks import check_answer_form
from .generation import prepare_context
from .routing import Capability


def prepare_live(query, config, tokenize):
    if config["generator"]["dtype"] != "float32":
        raise ValueError("live worker requires the checked float32 generator")
    if config["sampling"] is not False or config["max_new_tokens"] != 96:
        raise ValueError("live worker requires greedy decoding and the pinned 96-token reserve")
    if config["total_tokens"] != 2048:
        raise ValueError("live worker requires the pinned total request cap")
    prepared = prepare_context(
        query, config, "fixed_web", tokenize, (Capability("web", True, False, None),)
    )
    return prepared


def finish_live(query, config, prepared, output_ids, prediction, elapsed, runtime):
    """Validate and package actual engine output; caller must decode from these IDs."""
    if len(output_ids) > config["max_new_tokens"] or any(
        type(i) is not int or i < 0 for i in output_ids
    ):
        raise ValueError("invalid live output token IDs")
    if len(prepared["input_ids"]) + config["max_new_tokens"] > config["total_tokens"]:
        raise ValueError("live request exceeds full token budget")
    if not output_ids or not prediction.strip():
        raise ValueError("live generator returned no answer")
    if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
        raise ValueError("finite nonnegative live timing required")
    return {
        "mode": "new_gpu_generation",
        "interaction_id": query.interaction_id,
        "query": query.query,
        "query_time": query.query_time,
        "policy": "fixed_web",
        "prediction": prediction,
        "prompt_sha256": hashlib.sha256(
            json.dumps(prepared["messages"], ensure_ascii=False).encode()
        ).hexdigest(),
        "selected": prepared["evidence"],
        "input_tokens": len(prepared["input_ids"]),
        "output_tokens": len(output_ids),
        "output_ids": output_ids,
        "maximum_reserved_tokens": len(prepared["input_ids"]) + config["max_new_tokens"],
        "actual_llm_calls": 1,
        "actual_source_calls": prepared["source_calls"],
        "generation_seconds": elapsed,
        "runtime": runtime,
        "answer_form_checks": check_answer_form(
            query.query, prediction, [e["evidence_id"] for e in prepared["evidence"]]
        ),
        "citation_status": "Selected input evidence; claim-level support remains unverified.",
        "scope": "Live adapted web-only demonstration, separate from frozen experiments.",
    }


def generate_one(query, config, root):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, LogitsProcessor

    if not torch.cuda.is_available():
        raise ValueError("actual CUDA GPU required; no replay fallback")
    model_dir = root / config["generator"]["directory"]
    tokenizer = AutoTokenizer.from_pretrained(
        model_dir, local_files_only=True, trust_remote_code=False
    )
    prepared = prepare_live(
        query,
        config,
        lambda m: tokenizer.apply_chat_template(m, tokenize=True, add_generation_prompt=True),
    )
    torch.manual_seed(config["seed"])
    torch.cuda.manual_seed_all(config["seed"])
    torch.backends.cudnn.benchmark = False
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
        raise ValueError("nonfinite live model parameters")

    class FiniteScores(LogitsProcessor):
        def __call__(self, input_ids, scores):
            if (
                torch.isnan(scores).any()
                or torch.isposinf(scores).any()
                or not torch.isfinite(scores).any(dim=-1).all()
            ):
                raise ValueError("nonfinite live generation scores")
            return scores

    inputs = torch.tensor([prepared["input_ids"]], device="cuda:0")
    torch.cuda.synchronize()
    started = time.perf_counter()
    with torch.inference_mode():
        generated = model.generate(
            input_ids=inputs,
            attention_mask=torch.ones_like(inputs),
            max_new_tokens=config["max_new_tokens"],
            do_sample=False,
            num_beams=1,
            temperature=None,
            top_p=None,
            top_k=None,
            logits_processor=[FiniteScores()],
            pad_token_id=tokenizer.eos_token_id,
        )
    torch.cuda.synchronize()
    ids = generated[0, inputs.shape[1] :].cpu().tolist()
    return finish_live(
        query,
        config,
        prepared,
        ids,
        tokenizer.decode(ids, skip_special_tokens=True).strip(),
        time.perf_counter() - started,
        {
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0),
            "dtype": "float32",
            "per_step_scores_guarded": True,
        },
    )
