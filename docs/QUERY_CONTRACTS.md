# Partial query contracts — development checkpoint

The query-only contract extractor records exact spans for explicit ISO dates, decades,
counts, top-N lists, opening/closing prices, negative eligibility words and a small
relative-time vocabulary. Requirements come from the question alone. Negative and
relative-time mentions are hints, not resolved predicates or calendar dates.

The diagnostic flags only narrow observable conflicts: an explicitly all-time answer
for a single decade request, an explicitly opposite opening/closing price field,
or one explicit `as of DATE` answer differing from one `on DATE` request. Quoted,
negated and comparison answers are conservatively skipped. Multiple requested dates
or decades remain unresolved. Existing identifier/list/rectangle checks are retained.
A bare number has no asserted period, field or entity and cannot be verified this way.

Every result preserves the raw answer and binds the query, prediction and selected
source identities. `answer_accepted`, factual verification and claim support remain
false for every result, including responses with no detected issue. This is a partial
contract diagnostic; entity roles, semantic relations, units and full completeness
remain unfinished. It is separate from the live API and does not change frozen
outputs, answer scoring, selection or the demo's acceptance behavior.

## Executed replay

[The source-bound replay](../results/version1/answer_contracts_replay.json) covers all
444 admitted response records. It records admission and implementation hashes,
per-response bindings, requirement spans, diagnostics and status counts. No reference
answer or review label enters extraction. No new model call occurs.

There are 12 review-required responses, 137 exact generator abstentions and 295
unresolved responses. All 12 warnings reproduce existing form checks. The new explicit
scope checks add **zero** findings on this inspected replay. This is not evidence of
semantic improvement: the observed cohort's wrong-period answers often contain only
a number or omit their period. Prose abstentions beyond the existing exact detector
also remain unresolved. Do not score these counts as answer quality or accuracy.

Fresh synthetic tests cover differing dates, invalid calendar dates, negated scope,
comparisons, conflicting price fields, missing fields and binding changes. These tests
establish bounded behavior, not measured performance on fresh research questions.

## Reproduce

From the repository root:

```sh
uv sync --locked --no-editable --extra demo
uv run --locked --no-editable pytest -q tests/test_answer_contracts.py
uv run --locked --no-editable python scripts/answer_contracts_replay.py \
  --output runs/query-contracts/replay.json
```

The output must be new; the replay refuses to overwrite an existing artifact. Local
admitted traces are required; their exact hashes are verified before processing.
Missing traces retain their unavailable state, rather than acquiring invented outputs.

## Next gate

Build structured source claims with explicit entity, metric, unit and period, retaining
exact supporting spans. Compare those claims to query requirements without supplying
reference answers. Measure false alarms and missed requirements on fresh reviewed
cases before enabling any automatic acceptance. Keep the unframed NLI diagnostic
separate: source entailment alone did not establish that an answer satisfied a question.
