# Typed query graph v2 — executed and reviewed diagnostic

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

## Completed execution and AI review

The isolated GPU worker, bundle isolation test and synthetic output reconstruction
test are implemented. Private Kaggle kernel
`ionrey/ace-qg2-a22c852d067f4ab8ad7b43804c946d2c`, version 1, completed.
The [execution proof](../results/version1/query_graph_verification.json) reconstructs
all fifty sequences and thirteen invocations: 65,978 input tokens, 66,326 padded
inputs, 11,600 output tokens, 3,405 maximum reserve, 562.72 seconds generation and
11.00 seconds model loading. No requests were skipped or capped. The submitted
bundle, canonical grammar, decoded tokens, spans, progress and costs match.
The [submission receipt](../results/version1/query_graph_submission.json) preserves
its original RUNNING observation; completion is proved separately.

Forty-eight graphs remain unresolved; two are structurally linked (indices 21 and
35). Initial inspection shows that the first drops top-ten cardinality and ranks
a query-time anchor with SPY as candidate. The second treats the unresolved latest
president description as a context constant and misbinds the spouse relation.
These are semantic errors despite structural linking, not evidence of improved
answer quality. The [review proof](../results/version1/query_graph_review_progress.json)
now binds all fifty proposals to their exact query, raw output and validation. All
151 query-only checklist items were assessed. Three graphs preserve coherent
partial cores (indices 3, 6 and 20), while 47 are misbound or incomplete. All fifty
remain incomplete; these categories are qualitative AI judgments, not independent
accuracy. No reference answer, generated answer or source excerpt was used for
this query-only requirements assessment.

Neither the grammar nor its validator verifies complete question interpretation,
source support, units compatible for computation, factual truth or answer quality.
Date and period recognition is bounded lexical syntax, not calendar validation.
Ranked set element types and operand/candidate semantic alignment need review.
Operations are proposed, not executed. The input cohort has already been seen
and cannot provide fresh evaluation accuracy. Independent requirements/support
labels and a fresh cohort remain necessary for scientific promotion.

GPU output reconstruction command after provider completion:

```sh
uv run --locked --no-editable --extra generation --extra constraints \
  python scripts/verify_query_graph.py \
  --bundle runs/version1/query-graph-kernel-v2 \
  --run runs/version1/query-graph-output-v2/query-graph-pilot \
  --source-trace runs/kaggle/cohort-output-v1/cohort-pilot/generated/predictions.jsonl \
  --output runs/version1/query-graph-verification-v2.json
```

## Reproduce review verification

```sh
uv run --locked --no-editable --extra generation --extra constraints \
  python scripts/verify_query_graph_reviews.py \
  --output runs/version1/query-graph-review-verification-repeat.json
```

The checker freshly reconstructs the complete GPU execution before admitting the
review batch. It preserves the original v1 query-only checklist because task
identities are unchanged, verifies its original bundle binding, then rejects
missing checks, changed text/output hashes, incomplete coverage, duplicate tasks
and forged human/coverage/acceptance claims. Raw traces, checklist and review
batch are private local artifacts; the public ledger binds their hashes.
