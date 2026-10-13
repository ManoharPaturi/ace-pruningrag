# Closed-span extraction — separate bounded experiment

The [completed unconstrained control](STRUCTURED_CLAIM_EXTRACTION.md) produced no
contract-valid query proposals. This experiment changes the decoder's permitted
outputs while preserving the same 386 blinded tasks, prompts, generator, seed,
float32 eager attention, batches of four and token caps. It does not repair or
replace any retained output or baseline answer.

## Permitted outputs

Each task compiles a fixed-order JSON object with six keys. Every field is JSON null
or a canonical JSON string for a contiguous range of lexical/punctuation tokens from
that task's exact text. Internal whitespace, Unicode, quotes and backslashes are
preserved. Punctuation boundaries allow `Harvey Specter` to be selected separately
from the question mark in `Harvey Specter?`. Arbitrary word fragments and normalized
or invented values are outside the choices. Query `value` is forced to JSON null.

The source remains capped at 160 whitespace words and 640 lexical/punctuation atoms.
These are explicit input limits, not truncation. All 386 current tasks fit: maximum
120 words and 599 atoms. The original 2,048 full-request and 160-output-token limits
still apply. Long outputs may reach the output cap before completing their object;
these failures must remain visible and cannot be accepted.

The pinned [LM Format Enforcer project](https://github.com/noamgat/lm-format-enforcer)
provides character-parser/tokenizer enforcement interfaces. Tests of its 0.11.3
JSON-schema enum parser rejected legitimate escaped-quote choices. This implementation
therefore builds a trie of exact JSON string representations, combines it with fixed
key sequences, and uses the library's token enforcer. It does not drop quoted source
spans to work around the parser behavior. Each batch item has its own parser; tokenizer
preprocessing is shared. The installed source and its integration API were inspected.

New optional `constraints` dependencies are locked in `uv.lock`. The private GPU overlay
pins the enforcement dependencies separately from the original inference dependencies.
It uses `--no-deps --target`; the base environment is preserved. The experiment's
runtime versions and all constraint dependency versions must be recorded and checked.

## Execution state and bounds

Private kernel `ionrey/ace-constrained-2588acf828b5428082b6f66256a1632c`, version 1,
completed and passed full input/output/span/cost reconstruction. [Submission record](../results/version1/constrained_submission.json)
binds the original trace, blinded task payload, control trace and protocol.
[Reconstruction](../results/version1/constrained_verification.json) checks all 386 outputs.
[Control comparison](../results/version1/constrained_control_comparison.json) confirms identical
tasks, prompts, input token counts and generator configuration. Full semantic role
review remains pending; completion of execution is not completion of verification.

The run permits at most 386 extraction sequences, 97 model `generate` invocations,
61,760 output tokens and 790,528 cumulative reserved request tokens. All extraction
calls count separately from baseline answer generation. No new baseline answer call
is requested. Padding and actual output tokens must be reconstructed. Model loading
and generation timings are partial: schema/trie preparation, tokenizer preprocessing,
queue, download and setup are excluded from those timings.

## Validation and next gate

Fresh tests use the real character parser and token enforcer to check forbidden fields,
query answers, invented dates/entities, malformed objects, premature EOS, incomplete
outputs, punctuation, internal whitespace, escaped quotes, Unicode and input caps.
The token-enforcer test uses a synthetic tokenizer and proves filter behavior only;
it is not an actual Qwen or GPU generation test. Local validation passes 180 tests.
The required CI test job installs the `constraints` extra so these tests cannot silently
skip because the library is missing.

After remote completion, download to a fresh directory and reconstruct with:

```sh
uv run --locked --no-editable --extra generation --extra constraints \
  python scripts/verify_constrained_extraction.py \
  --bundle runs/version1/constrained-kernel-v1 \
  --run runs/version1/constrained-output-v1/constrained-pilot \
  --source-trace runs/kaggle/cohort-output-v1/cohort-pilot/generated/predictions.jsonl \
  --output results/version1/constrained_verification.json
```

The verifier checks submitted source, blinded tasks, full tokenizer inputs, decoded
IDs, exact allowed span membership, completed canonical object order, token caps,
progress, cumulative costs and dependency versions. It does not independently rerun
neural generation or prove semantic correctness. Outputs and verification paths must
be new; never overwrite the unconstrained control.

**A complete grammar-conforming object can still mix unrelated facts or assign a
competition stage to a unit.** Every proposal retains `semantic_tuple_verified=false`,
`source_truth_verified=false`, `answer_accepted=false` and incomplete claim coverage.
Review field roles against complete excerpts and evaluate full requirement/support
coverage before using these proposals. Fresh independent review, cross-source/source-only
controls and the other open roadmap gates remain required.


## Completed structural outcomes and partial role audit

| Input kind | Control span-valid | Constrained span-valid | Constrained cap failure |
| --- | ---: | ---: | ---: |
| 50 questions | 0 | 50 | 0 |
| 336 excerpts | 6 | 335 | 1 |

All 386 sequences / 97 batch invocations were reconstructed. Inputs are 124,383
unpadded / 148,610 padded tokens; outputs are 16,198 tokens; maximum request reserve
is 890. Generation took 433.46 seconds and model load 6.82 seconds. These timings
exclude constraint/trie preparation, tokenizer preprocessing, queue, acquisition and
setup. Do not claim improved end-to-end latency from them. The one cap failure remains
invalid JSON; it is not repaired or counted as valid. No baseline answer changed.

[Literal alignment](../results/version1/constrained_alignment_replay.json) yields
950 unresolved and 155 different-field comparisons across 1,105 selected pairs.
No pair has complete unambiguous literal field alignment. Different strings can be
aliases or paraphrases; these counts are not semantic support or accuracy. All results
retain acceptance disabled.

[Role-review progress](../results/version1/constrained_review_progress.json) binds
50 question proposals with AI rationales plus the one deterministic cap-failure
assessment. Post-hoc query review identifies 48 partial/misbound requirements, one
coherent minimal count core and one underspecified query scope. These are qualitative
AI diagnostic categories, not independently validated extraction accuracy. Typical
failures include a second comparison entity omitted, movie-title words assigned to
period, question marks assigned to unit and a negative eligibility placed in unit.
**All 335 span-valid source proposals still require role review.** Structural success
does not authorize general verification, factual support or answer acceptance.

The current partial review bindings can be checked with:

```sh
uv run --locked --no-editable python scripts/verify_constrained_reviews.py
```

Full private review records are required. The verifier recomputes coverage and rejects
changed inputs, proposals, identities, batch hashes, counts or human-review promotion.
The report remains partial until every source proposal is assessed. Earlier queued
status is historical; do not resubmit this completed kernel.


### Source-role review checkpoint and lexical defect

The first 100 valid source proposals have bound AI rationales: 45 mixed facts,
20 partial bindings with role errors, 20 role/scope errors, eight metadata/nonclaim
proposals, four missing subjects/antecedents and three coherent reported claims.
These are 90 distinct text/proposal pairs; the three coherent records represent
two distinct pairs. They are not independent confirmations or calibrated accuracy.
235 valid source proposals remain unreviewed. The current source-review counts
are recomputed from private batch records by the review verifier.

The [Unicode counterexample](../results/version1/constrained_unicode_counterexample.json)
shows the frozen lexical policy permitting `Victoria Mone` before the combining
accent and final `t` in the full source name. The regex splits the combining mark
as punctuation, exposing an unintended within-word boundary. Structural acceptance
under that policy does not establish a complete entity name. Preserve the exact
control outputs and submitted source; fix the lexer with combining-mark-aware
boundaries in a separately versioned implementation, then revalidate affected
choices. This correction does not resolve broader entity/role or comparison loss.
Earlier counts of zero source review are historical; read the current progress JSON
for the latest coverage. No source proposal is promoted to an accepted answer.


The [binding-check record](../results/version1/constrained_review_binding_checks.json)
confirms local rejection of altered source-category counts, a promoted human-review
flag and a replacement verification file not bound to these outputs. The checks use
temporary copies/symlinks for reading; original experiment and audit artifacts are
not modified. They protect bookkeeping, not the correctness of AI judgments.


The [versioned combining-mark correction](UNICODE_SPAN_POLICY.md) is now implemented
and replayed against all old outputs. The submitted v1 control remains intact; do not
reinterpret its 385 valid proposals as corrected-policy generation results. The v2
policy rejects the observed truncated name. Corrected neural execution and the full
source-role audit are still pending. Earlier instructions to fix that boundary are
superseded by this implementation checkpoint.


### Source-role audit at 150/335

Current review coverage is 150 source records / 136 distinct text-proposal pairs,
plus all 50 query proposals and the cap-failure assessment. Seven coherent-claim
records represent five distinct pairs. They include reported historical/relative
claims and metadata such as playlist update frequency; none is automatically an
answer to its associated question or external factual confirmation. There are
185 source proposals remaining. Source-category counts and pair deduplication are
recomputed from every bound private batch. Earlier 100-record counts are historical.


### Source-role audit at 200/335

The fifth private batch brings source coverage to 200 records / 181 distinct
text-proposal pairs. Ten coherent-claim records represent eight distinct pairs.
They include a reported forecast, a dated quote, one title win and update-frequency
metadata; these categories must not become verified current answers. There are
135 valid source proposals pending, plus 50 completed query reviews and the one
assessed cap failure (251 bound records total). Latest failures include actor/character
inversion, a lost negative career statement, denominator-as-goals confusion,
construction/location/cost mixing and puppet-versus-film-versus-photography durations.
All interpretation remains qualitative AI-assisted excerpt review.


### Source-role audit at 250/335

The sixth private batch brings source coverage to 250 records / 225 distinct
text-proposal pairs. Twelve coherent-claim records represent ten distinct pairs;
all remain qualified source reports, not accepted or externally verified answers.
There are 85 valid sources pending. Together with 50 query reviews and the cap
failure, 301 records bind to the frozen tasks and raw proposals.

New observations include cross-row lake facts, a website statistics cutoff assigned
to a navigation team, tour completion mixed with album development, incomplete
currency amounts, and reported plans or rumors losing their attribution. Competition
names, stages and publication outlets also appear as measurement units. Complete
requirements, calibrated accuracy and independent human review remain unverified.
Earlier checkpoints are historical; the progress artifact holds current counts.


### Complete proposal-role audit: 335/335 valid sources

All 386 tasks now have a bound assessment: 50 query proposals, 335 valid source
proposals and the capped invalid source. The final 85-record batch leaves no
unreviewed valid proposals. Source categories are 120 mixed facts, 82 partial
bindings with role errors, 56 role/scope errors, 39 metadata/nonclaims, 23 missing
subjects/antecedents and 15 coherent excerpt claims. The 335 source records contain
300 distinct text/proposal pairs; the 15 coherent records contain 13 distinct pairs.

These are post-hoc qualitative AI categories, not a calibrated extraction score.
Full semantic review complete means task-level role assessment coverage only; it
does not establish external truth, independent human review, complete atomic
requirements, all claims in each excerpt or accepted answers. Those flags remain
false, and the original model outputs and validation counts remain unchanged.

The final batch exposes ownership-direction reversal, institutional investor sales
assigned to an individual, offer/closing-price distinctions, award nominations
turned into wins, commentator biographies mixed with actor facts, and questions
converted into assertions. Lake visit seasons and organism geological eras are
also incorrectly used as measurement dates. The source-only coherent claims include
reported historical IPO pricing, a relative brand count and a dated reservoir
elevation; none is proof of present values or a complete answer to its query.

Next, run the separately versioned Unicode policy with the fixed GPU controls, then
implement atomic claim/requirement representation and conservative role/support
checks. JSON grammar and exact substrings cannot resolve the observed errors.
