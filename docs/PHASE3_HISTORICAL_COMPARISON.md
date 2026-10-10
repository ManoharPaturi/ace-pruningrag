# Historical routing diagnostic

This bounded development experiment uses the six query IDs frozen by the
previous full-dataset price eligibility audit. Questions ask for a prior-day
closing price and have exact dated rows in the immutable original CRAG snapshot.
The questions were selected for executable source availability, not answers or
model performance. This is not a representative RM3QA benchmark or the original
PruningRAG reproduction.

## Frozen comparison

- Six same questions under fixed-web, all-available, and heuristic adaptive routing.
- Original pinned Qwen2.5-1.5B-Instruct revision, float32 numerical guards, seed 42,
  greedy decoding, system prompt, top-K selector, web pool and chunking unchanged.
- Shared 2,048-token total request cap, with 96 output tokens reserved. Actual
  chat templates, question/time, headers, separators and evidence count toward it.
- API evidence contains the requested earlier closing price, exact original row
  timestamp, immutable snapshot hash, and explicit unspecified currency/basis.
  Missing dates never fall back to a different price. Same-day completed prices
  cannot answer a morning question in this adapter.
- Each policy genuinely executes its allocated sources; record preflight lookup,
  retrieval and generation costs separately. Rotate execution order per question.
- Keep the adaptive hint rules unchanged: they miss two closing-price phrasings.
  Adaptive requests four API rows; all-available six; fixed-web zero. The different
  source allocations are part of the result, not retuned using generated answers.
- Gold answers enter post-generation literal agreement only. Non-exact answers
  remain pending semantic review; literal disagreement alone is not incorrectness.

The original first-50 configuration remains unchanged. The new configuration is
`configs/historical_routing.json`. CPU preparation verified all 18 prompts:
maximum prompt plus reserved output is 1,657 tokens. Model calls during this
preflight are zero.

## Reproduce

```sh
uv run --locked --no-editable --extra generation python scripts/historical_preflight.py \
  --output runs/new-historical-preflight
uv run --locked --no-editable python scripts/build_kaggle_kernel.py \
  --owner YOUR_ACCOUNT --mode historical --output runs/kaggle/new-historical-kernel
uv tool run --from kaggle==2.2.4 kaggle kernels push \
  -p runs/kaggle/new-historical-kernel -t 1800
```

The historical kernel has a separate private identity and preserves the original
first-50 kernel. Only allowlisted code and pinned configs enter the bundle; human
reviews, credentials, raw datasets and weights stay excluded. Inference uses the
same isolated fresh-process dependency versions and records whether base package
versions changed.

Run `scripts/verify_generated.py --run PATH/phase3-pilot/generated` with the
generation extra after downloading outputs. The verifier independently checks
original web spans and dated SQLite values, reconstructs API identity, prompts,
token/output decoding, per-source/full budgets, source/model counts and summaries.
It also remains compatible with the earlier first-50 trace.

The required finance-smoke CI job prepares all 18 requests with the actual model
tokenizer and original historical prices. Unit tests and real-source preparation
are development checks; GPU execution and recovered-output verification are
separate requirements.
