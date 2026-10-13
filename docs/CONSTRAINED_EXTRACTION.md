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
was submitted successfully and observed **QUEUED**. [Submission record](../results/version1/constrained_submission.json)
binds the original trace, blinded task payload, control trace and protocol. Completion,
output reconstruction, role audit and control comparison are **pending**. Poll the
same kernel; an observation failure is not grounds for resubmission.

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
