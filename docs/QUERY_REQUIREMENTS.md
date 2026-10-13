# Query requirements with unknown answers

The frozen plural-inventory control forced every query value to null. That excluded
guessed answers but also lost explicit conditions such as “14 awards.” The separately
versioned `query_requirements.py` represents known conditions and unknown answers
independently. Existing GPU protocols, raw outputs and submitted modules are preserved.

Each proposal has status, composition, cardinality, variables, clauses and operation.
Up to eight sequential variables and twelve clauses are allowed. Answer variables
and latent intermediate variables have null constants. Context variables copy exact
question spans. The first variable is an answer variable; empty ambiguous proposals
remain possible and receive missing-structure warnings.

For “Who won 14 awards and was born in 1990?”, an unknown subject variable can bind
both clauses, while 14 and 1990 remain explicit copied conditions. Comparisons can
link two context entities to distinct unknown measurements and an unknown result.
Calculation proposals can link copied numeric operands to an unknown output; this
module neither calculates a result nor supplies an answer.

Subject, object, value and period fields contain a copied span, a declared variable
reference or null. Relations, units and qualifications are copied clause-local spans.
The validator checks Unicode lexical boundaries, clause-local occurrence offsets,
variable roles, constant restrictions, operation arity and self-dependencies. Query
time remains an authoritative input anchor. Relative dates are not resolved.

The canonical character grammar enforces field order, bounds, sequential IDs, declared
references, copied query spans and null answer/intermediate constants. It permits
global spans and declared references without proving local role coherence. Every
decoded output must subsequently pass the validator. Even a bound proposal leaves
semantic requirements, complete coverage and answer acceptance explicitly false.
Repeated operands, relation meaning, cardinality meaning, negation scope and temporal
meaning still require semantic review; syntax cannot establish these.

Nine tests cover explicit numeric conditions, shared unknowns, comparisons,
calculation references, label blinding, combining marks, limits and decoder rejection
of invented or undeclared values. A real token-enforcer test with a synthetic
character tokenizer checks that termination is permitted only after a full proposal. Tests also demonstrate that grammar-admitted
cross-clause spans, wrong-role references and wrong arity fail validation.

```sh
uv run --locked --no-editable --extra constraints \
  pytest -q tests/test_query_requirements.py
```

This checkpoint implements representation, prompting, decoding grammar and validation.
A separate query-only protocol has now been submitted on the fifty existing
development questions. Neural quality is not measured yet; reconstruct outputs and
full extraction budgets before reviewing roles and omissions. Retain the
negative inventory control and keep answer-generation settings fixed. The source
statement/context protocol and web/API support composition remain subsequent work.
Fresh independently reviewed evaluation remains a separate scientific gate.


## Frozen query-only GPU diagnostic

`configs/query_requirements.json` pins the prompt/grammar hash, eight variables,
twelve clauses, 2,048 output tokens, 4,096 total tokens, FP32 and seed 42. The query
prompt and representation differ from the frozen inventory control; improvement
must be measured, not inferred. The answer generator is unchanged.

[Tokenizer preflight](../results/version1/requirements_preflight.json) verifies all
50 requests: 31,078 input tokens and 2,707 maximum input-plus-output reserve. It
makes no model calls. The private bundle excludes source excerpts, predictions and
reference answers, retains task identities and permits at most 13 generate calls.

[Submission](../results/version1/requirements_submission.json) records version 1 of
`ionrey/ace-requirements-0f48b7f420a648cdbf532361c3fd13a8`, observed RUNNING.
Keep this identity and collect its terminal output rather than submitting a duplicate.
All 219 local tests pass, including protocol drift and label/source isolation tests.

```sh
uv tool run --from kaggle==2.2.4 kaggle kernels status \
  ionrey/ace-requirements-0f48b7f420a648cdbf532361c3fd13a8
uv tool run --from kaggle==2.2.4 kaggle kernels output \
  ionrey/ace-requirements-0f48b7f420a648cdbf532361c3fd13a8 \
  -p runs/version1/requirements-output-v1
uv run --locked --no-editable --extra generation --extra constraints \
  python scripts/verify_requirements_extraction.py \
  --bundle runs/version1/requirements-kernel-v1 \
  --run runs/version1/requirements-output-v1/requirements-pilot \
  --source-trace runs/kaggle/cohort-output-v1/cohort-pilot/generated/predictions.jsonl \
  --output results/version1/requirements_verification.json
```

Reconstruction checks bundle/source hashes, blinded inputs, decoded token IDs,
canonical grammar (including incomplete capped prefixes), independent validation,
input/padding/output/call costs, progress, runtime and dependency isolation. This
checks recorded execution, not an independent rerun of neural inference. Review all
fifty questions for misbound roles, lost constraints and omitted requirements before
promotion. A structurally valid proposal remains semantically unverified.


## Completed execution and all-output role review

Version 1 completed and [execution reconstruction](../results/version1/requirements_verification.json)
checks all fifty tasks, 13 generate calls, 31,078 input tokens, 31,426 padded input
tokens, 12,184 output tokens and 2,707 maximum reserved request tokens. Generation
took 494.744 seconds; model loading took 6.717 seconds. The generation interval
includes token filtering and excludes preparation/setup. There are no capped or
unextracted outputs and no new answer generations.

All fifty outputs are complete JSON but fail requirement validation. The
[all-output AI role review](../results/version1/requirements_review_progress.json)
reconstructs execution again and binds every exact input/proposal to a private
query-only checklist and review. All fifty show misbound or incomplete requirements.
This is qualitative AI review, not independent semantic accuracy. Reviewed coverage
means every proposal was assessed; it does not verify exhaustive requirements.

Observed failures include using number answers as subjects, song/film names as
periods, non-count words as cardinality, missing measurement operands, duplicate
clauses and self-dependent operations. The singer query still fails to represent
explicit 14 as a bound award-count condition. The rectangle query retains 17/66 but
misbinds their roles and omits the area operation. Do not promote the schema merely
because it supports correct hand-written examples.

The query gate fails. Preserve this protocol/trace and test role-aware decoding and
extractor capacity as separately versioned factors with costs counted. Keep the
answer-generator control unchanged; do not weaken role validation or manufacture
independent labels. Full source-support composition and broader research remain open.

```sh
uv run --locked --no-editable --extra generation --extra constraints \
  python scripts/verify_requirements_reviews.py \
  --output runs/requirements-review-reconstruction.json
```
