# Blinded structured extraction — bounded development diagnostic

This component proposes fields for query requirements and source claims, preserving
exact text provenance. It begins general requirement/claim work beyond the historical
closing-price parser. It does not establish general verification or automatic acceptance.

## Input and execution contract

The frozen 250-answer cohort trace produces **50 query tasks and 336 distinct selected
source tasks**. Every policy's selected excerpt is represented, deduplicating equal
question/source identities and rejecting changed content under an existing identity.
Model prompts contain only a question or one excerpt. Generated answers, reference
answers and review labels are excluded. Query timestamps remain bound metadata; relative
dates are deliberately not resolved by this extractor. The inspected cohort is development
data and cannot become a fresh held-out evaluation.

The extractor uses the existing pinned Qwen2.5-1.5B model in float32 CUDA with eager
attention, seed 42, greedy decoding and its pinned generation configuration defaults.
This is a separate extraction experiment, not a new baseline answer run. It allows
386 sequences, batches of four, at most 160 output tokens and 2,048 full request tokens.
Oversized prompts are skipped without truncation. Preflight found all 386 eligible,
124,383 input tokens and a maximum request reserve of 890 tokens. Execution allows at
most 97 `generate` invocations, 61,760 output tokens and 790,528 cumulative reserved
request tokens. Padding and actual output counts are reported separately.

The private kernel `ionrey/ace-extraction-ac6191501df7406c88b41a8707d4c8c2`, version 1,
completed and its downloaded outputs passed full structural reconstruction. [Submission record](../results/version1/extraction_submission.json)
binds its payload, source trace, limits and preflight. [Reconstruction](../results/version1/extraction_verification.json)
checks every sequence; [complete audit](../results/version1/extraction_audit.json) records
structural failures and AI source review of all six span-valid proposals. These are
separate from admitted answer results and independent human evaluation.

## Proposal and validation

Each output must be one JSON object with exactly `entity`, `relation`, `period`, `unit`,
`predicate` and `value`. Every field is null or an exact case-sensitive substring of its
own input. Query extraction must leave `value` null. Source extraction proposes one
claim per excerpt; it cannot establish exhaustive claim coverage. A field copied from
the question cannot substantiate a source claim when absent from that source.

All occurrences of copied fields are retained as character offsets. Repeated text can
refer to different antecedents, so the comparison layer treats repeated positions as
ambiguous. Malformed JSON, wrong schemas, invented/normalized fields and proposed
query answers are retained as invalid outputs. There is no repair call or silent retry.
Raw output IDs and decoded proposals are retained, including output-cap failures.

Exact substrings can still come from unrelated sentences or carry the wrong role.
Consequently, span binding **does not prove a semantic tuple, truth or completeness**.
A literal field comparison only exposes matches/differences. Names and relations are
not silently canonicalized. Different strings may be aliases or paraphrases; they do
not establish an unsupported claim. Every result keeps acceptance disabled.

## Reconstruction and continuation

The verifier reconstructs blinded tasks from the original trace, checks submitted source
hashes, rebuilds complete tokenizer inputs, decodes outputs, revalidates spans and
reconciles calls, padded/unpadded tokens, terminators, caps and dependency isolation.
It does not independently rerun GPU neural generation or prove extraction accuracy.

The completed outputs are preserved in the paths below. To reconstruct to new output paths, run:

```sh
uv run --locked --no-editable --extra generation python scripts/verify_claim_extraction.py \
  --bundle runs/version1/extraction-kernel-v1 \
  --run runs/version1/extraction-output-v1/extraction-pilot \
  --source-trace runs/kaggle/cohort-output-v1/cohort-pilot/generated/predictions.jsonl \
  --output runs/extraction-reconstruction/verification.json

uv run --locked --no-editable python scripts/claim_alignment_replay.py \
  --bundle runs/version1/extraction-kernel-v1 \
  --run runs/version1/extraction-output-v1/extraction-pilot \
  --source-trace runs/kaggle/cohort-output-v1/cohort-pilot/generated/predictions.jsonl \
  --verification runs/extraction-reconstruction/verification.json \
  --output runs/extraction-reconstruction/alignment.json
```

Output paths must be new. If submitted source hashes later differ, reconstruct and
verify against the preserved submitted source snapshot; never relax hash checks.
Audit proposed tuples against their exact inputs before using them as requirements or
support features. Full claim lists, comparison operands, relative-date resolution,
semantic framing, measured extraction quality and independent fresh review remain
required. The [unframed NLI diagnostic](NLI_SUPPORT_DIAGNOSTIC.md) supplies evidence
against promoting raw entailment directly to answer acceptance.


## Completed results and retained failure decision

Actual execution generated 386 extraction sequences in 97 batched invocations,
using 124,383 unpadded / 148,610 padded input tokens and 17,991 output tokens. Model
loading took 7.09 seconds and generation 438.29 seconds; queue, download, setup and
local reconstruction are excluded. No new baseline answers were generated. Three
sequences reached the output cap without an EOS terminator; they remain retained.

| Input kind | Span-bound proposals | Invalid schema | Invalid proposal | Invalid JSON |
| --- | ---: | ---: | ---: | ---: |
| 50 questions | 0 | 6 | 44 | 0 |
| 336 excerpts | 6 | 1 | 264 | 65 |

These are contract-validation outcomes, not semantic extraction accuracy. Common
failures include invented dates, non-verbatim relations, nested period objects,
string `"null"` instead of JSON null and answering the query. All
[1,105 selected question/source comparisons](../results/version1/claim_alignment_replay.json)
are unresolved because no query proposal passes the contract.

All six span-valid proposals were AI-reviewed against their complete input excerpts.
Five still have role/scope problems: lost threshold inequality in the music list;
team/time fields used as units/values for Panthers elimination; games used as a
percentage unit; Amgen CEO, company description and index-membership period mixed;
and a playoff stage used as a measurement unit. The Lake Powell tuple follows a
historical 3,531-foot sentence dated September 3, 2022, but does not prove a current
level or external truth. Repeated spans remain visible. This six-case AI audit is
not independent human evaluation or a calibrated accuracy measurement.

**Do not promote this unconstrained extractor.** JSON instructions and substring
validation correctly expose failure but do not make a small generator obey the
contract or bind field roles. Next enforce schema/span choices during extraction,
then separately evaluate semantic relations, period attachment, negative predicates
and complete claim coverage. Keep this failed protocol and every raw proposal as
controls. Automatic acceptance remains disabled.

Full audit bindings can be checked with:

```sh
uv run --locked --no-editable python scripts/verify_extraction_audit.py \
  --source-trace runs/kaggle/cohort-output-v1/cohort-pilot/generated/predictions.jsonl \
  --extractions runs/version1/extraction-output-v1/extraction-pilot/extractions.jsonl \
  --audit runs/version1/extraction-ai-audit-v1.json \
  --verification results/version1/extraction_verification.json \
  --report results/version1/extraction_audit.json
```

The private full-text audit binds 386 records. Structural validation covers all 380
invalid proposals; the remaining six have explicit AI rationales. No invalid tuple is
silently salvaged or reclassified as correct. Seven additional synthetic tamper tests
check the reconstruction boundaries using a fake tokenizer; they do not claim GPU
execution. A cached vocabulary size avoids repeatedly allocating the full token map
while checking output IDs. Local validation now totals 175 passing tests.
