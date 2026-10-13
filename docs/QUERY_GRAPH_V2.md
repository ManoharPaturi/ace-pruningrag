# Typed query graph v2 — infrastructure checkpoint

The assistant owns continuation at the owner's request. The owner alone merges
main; implementation remains on draft PR #16 with required CI.

This is a separately versioned prompt, schema and decoding change. The failed
1.5B requirement control and matched 3B model variant retain their original
outputs and validation rules. V2 does not rescore them.

## Implemented

- Variables have a value type rather than one global argument position. A company
  can be subject of publishing and object of ownership in separate clauses.
- Known quantities remain copied context conditions. Unknown answer and latent
  values cannot be assigned invented constants. Query time stays an input anchor.
- Clauses bind inline literals to their own text and retain unit, period,
  qualification and positive/negative eligibility.
- Multiple operations can represent dependent calculations. Type, arity, result,
  candidate associations and dependency checks reject malformed plans. Context
  variables cannot be overwritten, and the answer cannot feed another operation.
- The immutable character grammar supplies the token filter with permitted JSON
  continuations. Complete synthetic JSON examples document the same contract.
- Empty roles, unused/disconnected variables and missing primitive facts remain
  unresolved. Structural linking never enables answer acceptance.

The cap is eight variables, twelve clauses and eight operations. The protocol
pins all three contract files, the existing 3B model and control decoding defaults.
The changed factor includes prompt, grammar and schema together; it is not a
measurement of model size alone.

## Verified so far

Ten graph tests cover shared entity roles, quantities, negation, combining marks,
query-time input, dependent calculations, candidate ranking, cycles, caps,
blinding, token filtering and parser immutability. The protocol test rejects
contract/budget/acceptance drift.

The [tokenizer receipt](../results/version1/query_graph_preflight.json) covers the
same fifty development questions as the controls: 65,978 input tokens, a maximum
reserved request of 3,405 tokens, and zero requests over the 4,096-token limit.
Every request reserves 2,048 output tokens. Preflight makes zero model calls.
Thirteen batch invocations would cover all fifty questions at batch size four.

Reproduce preflight with locally hash-verified tokenizer assets:

```sh
uv run --locked --no-editable --extra generation --extra constraints \
  python scripts/query_graph_preflight.py \
  --trace runs/kaggle/cohort-output-v1/cohort-pilot/generated/predictions.jsonl \
  --output runs/version1/query-graph-preflight-repeat.json
```

The source trace is private local development data; it is not committed. Task
construction strips reference answers, predictions and selected evidence before
creating model messages. The public receipt contains hashes and counts only.

## Pending execution and promotion

No v2 neural extraction run has been executed at this checkpoint. Next, build
and test an isolated GPU worker and output reconstruction, freeze its bundle,
run one bounded fifty-question diagnostic, then bind an AI assessment to every
exact output. Preserve capped, invalid and unresolved cases.

Neither the grammar nor its validator verifies complete question interpretation,
source support, units compatible for computation, factual truth or answer quality.
Date and period recognition is bounded lexical syntax, not calendar validation.
Ranked set element types and operand/candidate semantic alignment need review.
Operations are proposed, not executed. The input cohort has already been seen
and cannot provide fresh evaluation accuracy. Independent requirements/support
labels and a fresh cohort remain necessary for scientific promotion.
