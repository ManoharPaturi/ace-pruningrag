# Single-question live GPU worker

Updated 13 October 2026. A separate private Kaggle worker now performs **one actual generation** for a pinned question. It uses the existing float32 Qwen2.5-1.5B-Instruct, greedy seed-42 decoding, 96 output tokens and a 2,048-token complete request cap. This is a live-worker component; the browser job submission/polling bridge is still unfinished.

## Verified actual execution

Private kernel `ionrey/ace-live-2ec3b27e0524413680a7b5171e570d13`, version 1, completed. Request `2ec3b27e0524413680a7b5171e570d13` asks who directed Snow on tha Bluff. Its actual output is `Damon Russell`, with 1,206 input tokens, four output tokens, and a 1,302-token full reservation. Execution used Tesla T4 / torch 2.11.0+cu128 / float32; reported generation time is 1.67 seconds. This time excludes queueing, asset download, dependency installation and model loading, so it is not end-to-end latency.

[Independent reconstruction](../results/version1/live_worker_verification.json) checks submitted source/content hashes, output completion/result hashes, pinned query/source spans, reconstructed selection/prompt, decoding, token caps, dependency isolation and diagnostic fields. [Execution summary](../results/version1/live_worker_execution.json) keeps this one additional call separate from accepted experiment counts.

AI inspection found the answer directly supported by multiple selected director statements. It is one already inspected development question; this demonstrates worker execution, not held-out accuracy or general claim verification. Original experiment traces and their 444-record admitted set are unchanged. The raw output is private under `runs/version1/live-output-v1/live-answer/`.

## Implementation and boundaries

- [live_generation.py](../src/ace_pruningrag/live_generation.py) prepares query-only input, requires actual CUDA, guards finite float32 parameters/scores and packages actual output IDs, provenance and costs. It has no replay fallback and never evaluates against a gold answer.
- [live_driver.py](../scripts/live_driver.py) enforces isolated package versions and accepts only request ID plus pinned interaction ID. It writes a hashed result/completion pair.
- [build_live_kernel.py](../scripts/build_live_kernel.py) bundles first-party source and the dataset/generator configs into a private kernel with a unique request-specific name. It excludes raw traces, weights and credentials. Existing experiment kernel names are preserved.
- [verify_live_answer.py](../scripts/verify_live_answer.py) independently reconstructs the result against the submitted source version. It rejects changed identities, evidence, hashes, decoding, budgets and dependencies.

Unit fixtures test leakage boundaries, budget/protocol changes, output limits and bundle contents. They are not GPU observations. The actual GPU job above supplies execution evidence. All 152 local tests pass; Ruff lint/format and diff checks pass.

## Reproduce the admitted worker output

With owner-approved access to the private kernel, download to a fresh directory. The original submitted bundle is also needed for verification:

```bash
uv tool run --from kaggle==2.2.4 kaggle kernels output \
  ionrey/ace-live-2ec3b27e0524413680a7b5171e570d13 \
  -p runs/friend/live-output-v1
uv run --locked --no-editable --extra generation python scripts/verify_live_answer.py \
  --bundle runs/version1/live-request-v2 \
  --run runs/friend/live-output-v1/live-answer \
  --output runs/friend/live-worker-verification.json
```

Use the same submitted source version; later source changes intentionally require recovering its frozen checkout/bundle before reconstructing. A fresh clone lacks private bundles, raw results and model sidecars. Credentials stay outside Git and are not shared in the bundle.

## Remaining full-demo work

Add durable one-active-job submission/polling, request/result provenance validation, explicit queued/running/unavailable/failed states, restart recovery without duplicate submission, bounded total calls, and browser evidence rendering. Preserve the raw model output alongside any acceptance diagnostics. Claim-level support and entity/date/unit verification remain separate requirements. Do not label the current replay interface as a live generation flow before that complete boundary is verified.
