# Plural claim and requirement inventories

The completed six-field extraction audit shows that one tuple per excerpt loses
comparison operands and mixes actors, events, dates and units. The new
`src/ace_pruningrag/claim_inventory.py` provides a plural proposal representation
and separate query/source prompts. A separately versioned GPU inventory decoder is now submitted; its final outputs
and costs remain unverified. The completed six-field controls remain unchanged.

Each inventory contains at most 12 frames. Every frame has a supporting statement,
subject, relation, object, value, unit, event time, observation time, qualification
and attribution. Fields are exact source strings or null. Query-side values must
be null: requirements cannot contain a guessed answer. Several frames can retain
both sides of a comparison or separate events in one excerpt.

For example, `A bought B in 2001. C bought D in 2017.` has two separate proposed
frames. The validator rejects 2017 attached to the first statement. It also rejects
an `A` occurrence inside `CAT`, even when a separate standalone `A` occurs elsewhere
in the excerpt. It uses the corrected Unicode lexical boundaries and returns only
statement-local, boundary-valid source offsets, retaining all legitimate repetitions.

This limits an observed class of cross-statement mixing. A model can still choose
an overly broad statement, swap subject/object within it, misuse a date or omit a
claim. Structural validity therefore keeps semantic-role, source-truth, complete
requirement-coverage and answer-acceptance flags false. A proposed_complete status
is the extractor's claim; it never becomes verified completeness automatically.
Questions ending in a question mark receive an explicit assertion warning, but
this is not a general boilerplate/question classifier.

Qualification and attribution preserve text such as negation, estimates, bounds,
rumors, plans and reported statements. Event and observation dates have separate
fields; the validator does not infer temporal meaning or resolve relative dates.
Units remain proposed spans; it does not yet prove that a span is a measurement unit.

Six regression tests cover multi-event date isolation, directed role representation,
comparison operands, query answer exclusion and label blinding, qualifications,
observation dates, duplicates/caps, hallucinations, combining-mark truncation,
repeated text and question warnings. All 197 local tests pass with demo/constraints.

```sh
uv run --locked --no-editable --extra demo --extra constraints \
  pytest -q tests/test_claim_inventory.py
```

The versioned inventory decoder is now submitted with counted-call limits and full
prompt budgets. Its completion, output reconstruction and real role review are next. Keep the completed six-field runs as controls. Audit the real extracted
roles and completeness before composing support sets or integrating an acceptance
gate. The inspected cohort is development data; fresh evaluation and independent
labels remain separate requirements.


## Submitted plural decoder protocol

`configs/inventory_extraction.json` records the prompt/grammar module hash and
`inventory_frames_v1` identity. The closed grammar permits zero through 12 frames,
fixed key order and nullable exact source-span fields. Statement strings cannot be
null; query value fields are forced null. Literal JSON tries retain escaped quotes
and combining marks. Statement-local role binding is independently validated after
decoding; the grammar alone does not enforce semantic roles or local clause coherence.

Three decoder tests exercise complete objects, frame caps, empty text, quotes, Unicode,
query-answer exclusion and the real token enforcer using a synthetic tokenizer.
Two protocol/bundle tests reject drift in module/hash/budget/frame caps/acceptance
and inspect actual blinded payloads and worker imports. These five tests supplement
the six inventory-validator regressions. They do not demonstrate neural quality.

[Preflight](../results/version1/inventory_preflight.json) tokenizes all 386 real tasks
with the pinned generator tokenizer: 50 queries and 336 source tasks, 174,027 total
input tokens, 859 maximum input tokens and 2,907 maximum reserved tokens. All tasks
fit the changed 4,096 request cap with 2,048 output tokens reserved. Preflight makes
zero model calls. These changed prompts/budgets prevent a matched-budget improvement
claim against the previous 160-output/2,048-request controls.

[Submission](../results/version1/inventory_submission.json) identifies private kernel
`ionrey/ace-inventory-11f01825608146b2b9e913690b24bb45`, version 1, observed QUEUED.
The bounds remain 386 extraction sequences / 97 generate invocations, up to 12 frames
per task, with the same pinned Qwen, FP32, seed 42 and isolated dependencies. No new
baseline answers and no automatic answer acceptance. Preserve this kernel identity
and do not restart it because a status observation or download is unavailable.

After the provider reports terminal completion, download to a fresh path and verify:

```sh
uv tool run --from kaggle==2.2.4 kaggle kernels status \
  ionrey/ace-inventory-11f01825608146b2b9e913690b24bb45
uv tool run --from kaggle==2.2.4 kaggle kernels output \
  ionrey/ace-inventory-11f01825608146b2b9e913690b24bb45 \
  -p runs/version1/inventory-output-v1
uv run --locked --no-editable --extra generation --extra constraints \
  python scripts/verify_inventory_extraction.py \
  --bundle runs/version1/inventory-kernel-v1 \
  --run runs/version1/inventory-output-v1/inventory-pilot \
  --source-trace runs/kaggle/cohort-output-v1/cohort-pilot/generated/predictions.jsonl \
  --output results/version1/inventory_verification.json
```

Reconstruction checks submitted file hashes, blinded task identities, new prompts,
decoded IDs, closed ordered JSON, statement-local bindings, cap termination, progress,
input/padded/output costs, runtime and dependency isolation. Capped/invalid outputs
remain recorded. Audit the actual frames and omitted requirements before composing
support sets or promoting this representation into an acceptance path.
