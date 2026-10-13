# Controlled extractor model-variant diagnostic

The completed [1.5B query diagnostic](QUERY_REQUIREMENTS.md) produced fifty complete
JSON proposals, all rejected by requirement validation and all assessed for role
errors/omissions. This new trial changes the extractor checkpoint while preserving
that failed control. It does not change the answer generator or claim improvement.

The extractor is [Qwen2.5-3B-Instruct at the pinned revision](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/tree/aa8e72537993ba99e69dfaafa59ed015b17504d1).
The asset manifest records ten files totaling 6,183,458,486 bytes, including both
weight shards and their index. Only 11,531,494 bytes of small assets were fetched
locally; the private GPU worker fetches and verifies the weights. The model is under
the Qwen Research License, separately from the repository code license.

## Matched factors and changed factor

| Factor | Contract |
| --- | --- |
| Extractor checkpoint | Changed from the pinned 1.5B model to the pinned 3B model variant |
| Question tasks | Same fifty query-only tasks and exact task-payload hash |
| Prompt and grammar | Frozen `query_requirements.py`; no prompt/schema/role-validation changes |
| Encoded input IDs | Verified identical for every request using both actual tokenizers |
| Decode defaults | Original control file retained explicitly, including repetition penalty 1.1 |
| Output/request limits | Same 2,048 output / 4,096 full reserved tokens |
| Runtime settings | FP32, CUDA 0, eager attention, greedy, seed 42 and batch four |
| Costs | At most fifty extraction sequences / thirteen batched generate invocations |
| Baseline answers | No new answer generations; the answer-generator checkpoint stays unchanged |

The 3B model publishes a different default repetition penalty (1.05). The new
worker explicitly restores the control decoding configuration rather than silently
using that default. Input token hashes and decoding identity enter reconstruction.
Actual runtime versions/device must be compared after execution; matching requested
settings alone cannot prove identical environments. This changes model weights and
architecture as a model-variant factor, not a pure causal parameter-count experiment.

[Preflight](../results/version1/requirements_3b_preflight.json) fits all fifty tasks:
31,078 inputs and 2,707 maximum reserved tokens. The [matched-input receipt](../results/version1/requirements_3b_preflight_comparison.json)
checks task identities, prompts, spans, input token IDs and budgets against the frozen
control. Preflight makes zero model calls and establishes no extraction quality.

## Submission and collection

[Submission](../results/version1/requirements_3b_submission.json) identifies private
version 1 of `ionrey/ace-req3b-7f328043258c497fb9b1c758bbebf8c8`, observed RUNNING.
Two metadata submissions were rejected before creation. Authenticated inventory
checks found no corresponding jobs; the shorter matching title/slug was accepted.
The inference payload was unchanged. Preserve the successful identity and collect
its terminal output without submitting another run for an observation failure.

```sh
uv tool run --from kaggle==2.2.4 kaggle kernels status \
  ionrey/ace-req3b-7f328043258c497fb9b1c758bbebf8c8
uv tool run --from kaggle==2.2.4 kaggle kernels output \
  ionrey/ace-req3b-7f328043258c497fb9b1c758bbebf8c8 \
  -p runs/version1/requirements-3b-output-v1
uv run --locked --no-editable --extra generation --extra constraints \
  python scripts/verify_requirements_3b.py \
  --bundle runs/version1/requirements-3b-kernel-v1 \
  --run runs/version1/requirements-3b-output-v1/requirements-3b-pilot \
  --source-trace runs/kaggle/cohort-output-v1/cohort-pilot/generated/predictions.jsonl \
  --output results/version1/requirements_3b_verification.json
```

All 227 local tests pass. Three new tests cover asset/budget/default drift, blinded
bundling/naming, and synthetic execution reconstruction with changed input-token
hashes, costs and progress. The synthetic test is not a neural result. Required CI
now installs the generation extra and exercises this test rather than skipping it.

After completion, reconstruct every sequence and cost; compare runtime and decoding
identities and review all fifty outputs against the same query-only AI checklist.
Retain failed/capped cases. Structural admission is not semantic completeness or
independent human accuracy, and no answer-acceptance promotion follows automatically.
The original artifact, fresh independent evaluation, source support, cross-source
benefit, adaptive integration and final-paper gates remain open.
