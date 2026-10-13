# Plural claim and requirement inventories

The completed six-field extraction audit shows that one tuple per excerpt loses
comparison operands and mixes actors, events, dates and units. The new
`src/ace_pruningrag/claim_inventory.py` provides a plural proposal representation
and separate query/source prompts. The separately versioned GPU inventory decoder has completed; all outputs and
costs reconstruct. Its poor binding/role results below are retained. The completed six-field controls remain unchanged.

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
repeated text and question warnings. All 208 local tests pass with demo/constraints.

```sh
uv run --locked --no-editable --extra demo --extra constraints \
  pytest -q tests/test_claim_inventory.py
```

The versioned inventory decoder completed with counted calls and full prompt
budgets. Reconstruction and valid-output role review are recorded below. Keep the completed six-field runs as controls. Audit the real extracted
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


## Output audit before semantic review

`scripts/audit_inventory_extraction.py` requires and freshly reconstructs the
completed execution proof before auditing real outputs. It checks every task hash,
rejects duplicate/changed identities and reruns the frozen inventory validator.
It records query/source counts, parsed frame counts, structural admission, proposed
inventory states, warning distributions, nonnull roles and decoder cap flags.

Parsed and admitted frames are distinct: invalid inventories can contain parseable
frames, but none are promoted to structurally admitted frames. A capped incomplete
JSON output has no parsed frame count; this does not prove that its prefix contained
no attempted claims. Empty valid inventories are retained and still need review of
omitted requirements/evidence. Every task remains pending semantic review, including
proposed_complete inventories, questions and capped failures. The per-task ledger
binds input text and raw proposal hashes without publishing the full private text.

The audit is deterministic bookkeeping, not an AI/human correctness assessment.
It makes no new model calls and leaves role verification, complete requirement
coverage and answer acceptance false. Three tests reject identity/coverage/validation
tampering and confirm that questions, empty inventories, query-answer violations
and cap failures remain visible. The full 200-test suite passes.

Run only after the real job completes and its execution verifier succeeds:

```sh
uv run --locked --no-editable --extra generation --extra constraints \
  python scripts/audit_inventory_extraction.py \
  --bundle runs/version1/inventory-kernel-v1 \
  --run runs/version1/inventory-output-v1/inventory-pilot \
  --source-trace runs/kaggle/cohort-output-v1/cohort-pilot/generated/predictions.jsonl \
  --verification results/version1/inventory_verification.json \
  --output results/version1/inventory_structural_audit.json
```

That tooling checkpoint preceded completion. The actual audit and valid-output
review below now supersede the pending status. Rejected inventories still lack
full semantic assessment.


## Completed v1 inventory result

[Execution proof](../results/version1/inventory_verification.json) reconstructs 386
sequences / 97 invocations, 174,027 input tokens (198,260 padded), 176,078 output
tokens and 2,907 maximum reserved tokens. Generation took 7,848.47 seconds and loading
6.69 seconds. Token filtering during generation is included; constraint preparation
and other setup are excluded. Changed prompts/output limits prevent a same-budget
improvement claim against the earlier single-frame controls. No new baseline answers.

[All-task structural audit](../results/version1/inventory_structural_audit.json)
records 21 valid inventories, 361 binding/duplicate rejections and four capped JSON
failures. Queries contain 66 parsed frames and sources 1,551; only 20 query frames and
one source frame are structurally admitted. Partial prefixes of capped outputs are
not parsed/admitted, which does not mean no attempted frames were generated.
Source inventories include 82 proposed_complete labels; none establishes completeness.

[Bound AI review](../results/version1/inventory_valid_review_progress.json) covers
all 21 valid inventories. All 20 valid query inventories retain misbound roles, dates,
attribution or incomplete requirements. The single valid source is a conditional
L-shaped-room example with different operands from the question and full text in
time/attribution fields. These are qualitative judgments, not calibrated accuracy.
The 365 rejected inventories remain outside full semantic review, though their
structural issues, decoded IDs, inputs and costs are reconstructed. All acceptance
and independent-review flags remain false.

The global span grammar does not constrain roles to the chosen statement, so the
local validator reveals widespread violations. A separately versioned next grammar
should bind role choices to their statement and retain legitimately explicit source
context for attribution/observation metadata. This cannot itself establish semantic
roles. Query known constants must also be distinct from unknown answer variables: a
blanket query value-null rule cannot naturally represent a known 14-award constraint.
Do not relax validation or reuse invalid inventories merely to increase pass counts.
Preserve this failed control and measure each representation/model change separately.


## Extended rejected-output assessment

The [combined assessment progress](../results/version1/inventory_role_review_progress.json)
now binds all 386 tasks: fifty query inventories and 336 source inventories,
including all 365 rejected outputs beyond the original 21 valid-output reviews.
The 386 records contain 351 distinct input/proposal pairs and 1,617 fully parsed
frames. Thirty-five assessments reuse only exact identical input/proposal pairs.
No tasks remain unassessed. All four capped prefixes were inspected but contribute
zero fully parsed frames; partial JSON is never admitted as a complete inventory.
This completes the qualitative AI assessment, not independent accuracy, external
truth, exhaustive requirement coverage or answer acceptance.

Observed source problems include navigation labels as facts, photo dates attached
to vote/album events, year 2000 copied across unrelated election claims, missing
row/actor associations and procedural geometry examples promoted into assertions.
Partly coherent quantities/captions/reporting cores remain visible without proving
external truth or exhaustive coverage. These are qualitative AI judgments, not
independent human labels. Original execution/structural/valid-only proofs are unchanged.

```sh
uv run --locked --no-editable --extra generation --extra constraints \
  python scripts/verify_inventory_role_reviews.py \
  --batch runs/version1/inventory-rejected-ai-review-01.json \
  --batch runs/version1/inventory-rejected-ai-review-02.json \
  --batch runs/version1/inventory-rejected-ai-review-03.json \
  --batch runs/version1/inventory-rejected-ai-review-04.json \
  --batch runs/version1/inventory-rejected-ai-review-05.json \
  --batch runs/version1/inventory-rejected-ai-review-06.json \
  --batch runs/version1/inventory-rejected-ai-review-07.json \
  --batch runs/version1/inventory-rejected-ai-review-08.json \
  --batch runs/version1/inventory-rejected-ai-review-09.json \
  --batch runs/version1/inventory-rejected-ai-review-10.json \
  --output runs/inventory-role-progress.json
```

The checker freshly reconstructs the original execution and valid-output reviews,
then validates rejected input/output identities, frame counts, scope and exact reuse.
Two regression tests reject changed source text, proposal hashes, incomplete frame
assessment, duplicate identities, forged human/acceptance scope and unequal reuse.

The second rejected-output batch covers ten additional source tasks, including
one capped unparseable JSON output. Its visible repeated depth-claim prefix was
qualitatively assessed; it contributes zero fully parsed frames. Nine complete
outputs contribute 32 frames, including procedural examples, formula/navigation
mixing and Titanic role/date/attribution errors. No partial prefix is admitted
as a complete inventory. Three capped outputs still awaited assessment at that checkpoint. The seventh
batch subsequently assessed two of them; the final batch assessed the fourth. All
four capped failures now have exact-prefix assessments and zero parsed frames.

The third and fourth batches add thirty source assessments (179 parsed frames).
Exact input/proposal pairs 83/86 and 103/104 reuse identical judgments. Observations
include changed fictional/reporting scope, Marino/Rivers actor contamination,
relative-year leakage, sales/certified-unit confusion, dog advice/navigation and
sports/federation table cells treated as dated measurements. No factual accuracy
or full-support improvement is inferred from this qualitative review.

The fifth and sixth batches add sixty source-task assessments (261 parsed frames).
Six assessments reuse only exact input/proposal pairs, including repeated
sports-table, biography, photo-caption and franchise excerpts. Preserved partial
cores include Elle/179/LSAT, Olivia/Best-New-Artist/2022, Streep/narration and
Nexters/game-development wording. They remain accompanied by scope/date/unit/actor
errors and do not establish complete support or independent factual truth.

The new findings include bibliography retrieval dates used as award dates,
image indices used as film years, a date from one film attached to another,
actor-versus-character confusion and generic fund education treated as specific
financial events. Missing or paywalled values stay missing; N/A and Upgrade
are not numeric measurements. No additional experimental extraction or answer-generation calls were made.

The seventh and eighth batches add seventy source assessments (312 fully parsed
frames), including seven exact input/proposal reuses and two additional capped
JSON failures. The capped navigation-copy and repeated league-statistic prefixes
are assessed qualitatively and contribute zero fully parsed frames. Their raw
outputs and original extraction budgets remain unchanged.

Observed failures include annual-global versus current-USA music charts, playoff
elimination versus qualification, aggregate ETF concentration versus actual
holdings, actor/character reversals, match/season statistic confusion, forecast
horizon versus observation time and medal/title/player contamination. Useful
numeric cores remain visible without establishing complete source support or
external truth. No extra experimental model calls were made.


## Completed inventory assessment and next implementation

The last two batches assess the remaining 145 tasks and 691 parsed frames.
Failures include nomination-to-win substitutions, publication/reporting dates
used as event dates, IPO offering/closing-price confusion, paired-height collapse,
unanswered related questions asserted as facts and measurement/threshold swaps.
One reported album-status core is classified as coherent partial claims; this
does not establish current truth or complete support. Categories are qualitative
task judgments rather than calibrated accuracy labels.

The next protocol should extract atomic query requirements before compiling a
typed graph, then bind source claims separately. Preserve negation, reported and
hypothetical scope, actor pairs, quantity units, time windows and provenance.
Reject unanswered navigation questions and keep capped prefixes unresolved.
Use these inspected cases as development regressions; use fresh audited evidence
for scientific promotion. The original frozen decoder and outputs remain controls.
