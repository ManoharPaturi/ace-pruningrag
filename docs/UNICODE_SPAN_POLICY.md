# Versioned Unicode span-boundary correction

The source-role audit found the frozen v1 grammar permitting `Victoria Mone` inside
`Victoria Monét`. The combining accent was split as a punctuation atom, allowing a
model output to end inside the lexical name. This is an observed policy defect, not
an inference about model factual accuracy.

The corrected implementation is `src/ace_pruningrag/unicode_claims.py`. It groups
Unicode letters/numbers/underscore into lexical atoms, attaches Unicode combining
marks to the preceding base, and continues the lexical atom after those marks.
Whitespace and punctuation boundaries remain explicit. It never normalizes, rewrites
or repairs the input text; all source offsets and copied strings remain exact.

The old `constrained_claims.py` remains the frozen **v1 control** used by the submitted
GPU experiment and its reconstruction. The versioned module provides the corrected
**v2 policy** for subsequent decoder integration. Existing v1 generation scripts
continue to reproduce v1; no historical worker or admitted answer is silently migrated.
A corrected-policy worker has now been submitted separately; its completion and
reconstruction remain pending. It imports `unicode_claims.character_parser` and
records the explicit `unicode_combining_marks_v2` protocol and policy hash.

## Executed validation

Four regression tests exercise the observed name, nonspacing/spacing/enclosing mark
categories, multiple marks, exact offsets, punctuation/symbol marks, ASCII equivalence,
source-normalization rejection and nonacceptance flags. The real token enforcer with
a synthetic tokenizer cannot close the quoted entity before its combining suffix.
These tests prove the relevant filter behavior, not actual Qwen regeneration.

[Full replay](../results/version1/unicode_policy_replay.json) checks all **386 unchanged
old outputs** against both policies. Exactly one proposal changes classification: the
truncated entity is rejected under v2. The original capped invalid JSON remains invalid;
384 old proposals remain structurally permitted by v2. These are revalidations of
old outputs, not 386 new generations or newly reviewed factual claims. The replay
records both implementation hashes, original trace hash and zero new model calls.

Reproduce to a new output path:

```sh
uv sync --locked --no-editable --extra demo --extra constraints
uv run --locked --no-editable --extra constraints pytest -q tests/test_unicode_claims.py
uv run --locked --no-editable python scripts/replay_unicode_policy.py \
  --output runs/unicode-reconstruction/replay.json
```

The original private traces are required. The replay independently reconstructs each
v1 structural result before evaluating v2, rejecting any altered task or output binding.
Do not replace the original validation counts or AI review records with v2 counts.

## Limits and remaining work

This fixes combining-mark lexical boundaries. It does not establish full Unicode
extended-grapheme segmentation (such as all emoji/ZWJ sequences), named-entity
completeness across multiple words, entity aliases, semantic roles or factual truth.
A complete first name can still be an incomplete entity for a question. The separate
[proposal-role audit](CONSTRAINED_EXTRACTION.md) now covers all 386 tasks. Full claim coverage,
comparison operands, measured support and independent evaluation remain required.
Automatic acceptance remains disabled in both policies.


## Separate GPU protocol submitted

The [submission record](../results/version1/unicode_submission.json) identifies
private kernel `ionrey/ace-unicode-64945d4d23544527a191211fce4741e3`, version 1.
The provider reported RUNNING at the recorded observation. This is a submitted
execution, not a verified completion or improvement claim. Preserve this kernel
identity and poll it; an observation timeout is not permission to restart the run.

The builder, driver and independent verifier use `configs/unicode_extraction.json`
and check the corrected policy hash and unchanged v1 bounds. The same source trace
yields the identical task-payload hash, 50 queries and 336 source tasks. Generator
revision, prompts, FP32, seed, batch size and token limits remain the frozen controls.
The cap is 386 extraction sequences / 97 generation invocations, 160 output tokens
and 2,048 reserved tokens per task. No baseline answers are generated.

Two additional tests reject protocol, module, policy-hash, budget and acceptance
drift, and inspect the actual bundled driver and blinded task payload. Together
with the existing boundary/filter tests, all 186 local tests pass. These checks
validate setup; actual token IDs and measured GPU costs require collected outputs.

After terminal completion, download to a fresh directory and reconstruct:

```sh
uv tool run --from kaggle==2.2.4 kaggle kernels status \
  ionrey/ace-unicode-64945d4d23544527a191211fce4741e3
uv tool run --from kaggle==2.2.4 kaggle kernels output \
  ionrey/ace-unicode-64945d4d23544527a191211fce4741e3 \
  -p runs/version1/unicode-output-v2
uv run --locked --no-editable --extra generation --extra constraints \
  python scripts/verify_unicode_extraction.py \
  --bundle runs/version1/unicode-kernel-v2 \
  --run runs/version1/unicode-output-v2/unicode-pilot \
  --source-trace runs/kaggle/cohort-output-v1/cohort-pilot/generated/predictions.jsonl \
  --output results/version1/unicode_verification.json
uv run --locked --no-editable python scripts/compare_unicode_control.py \
  --run runs/version1/unicode-output-v2/unicode-pilot \
  --verification results/version1/unicode_verification.json \
  --output results/version1/unicode_control_comparison.json
```

The comparison checks task, message, input-token and model identity and retains
changed raw-proposal and token-ID hashes. Changed outputs require fresh role review.
Even unchanged text remains a qualitative source assessment, not an accepted answer.
