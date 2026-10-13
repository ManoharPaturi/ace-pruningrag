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
No corrected-policy GPU generation has been executed yet. A future worker must import
`unicode_claims.character_parser` and record that policy and its hash explicitly.

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
source-role audit still has 235 source proposals pending. Full claim coverage,
comparison operands, measured support and independent evaluation remain required.
Automatic acceptance remains disabled in both policies.
