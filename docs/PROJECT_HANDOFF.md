# ACE-PruningRAG: phase tracker and contributor handoff

**Updated:** 13 October 2026 (Asia/Kolkata)
**Repository:** https://github.com/ManoharPaturi/ace-pruningrag
**Main tracking-ref snapshot:** `ba30586ce85c15503a0df2ce4bb78a079c49e3ed`
**Merged work:** PRs #1–#15.
**Pending implementation:** [draft PR #16](https://github.com/ManoharPaturi/ace-pruningrag/pull/16), branch `feat/prospective-selector-evaluation`, verified implementation head `214905b` (before this documentation update).
**Local continuation state:** the five-selector GPU run and output verification are complete; cohort source review is 250/250 responses, and the replay/retrieval demo is implemented; see section 11. This file distinguishes these states so a fresh clone is not mistaken for the owner’s full workspace.

## Friend’s quick start — current checkpoint

**Start here:** PR #16 contains the latest implementation; merged main stops at PR #15. The owner alone merges main. Use your own fork and a feature branch as shown in section 11.

| Item | Current state | Next action |
| --- | --- | --- |
| Legacy development review | 150/150 AI-assessed responses; original 150 human records validated | Preserve original decisions; do not regrade silently |
| Historical/retry audit | 44/44 accepted response records AI-assessed | Reuse exact traces; repeated controls are not independent cases |
| Five-selector GPU experiment | 250/250 outputs verified across 50 questions | Reuse completed version 1; no new GPU run needed for review |
| Cohort AI source review | 250/250 responses, 50/50 questions | Read the completed audit; preserve AI/human separation and implement the prioritized fixes |
| Independent prospective evidence review | Pending | Import attested human requirements and support sets through the existing review workflow |
| Demo | 444 admitted replay records; fresh BM25 retrieval; HTTP/browser flow verified | Add and verify live generation and claim-level citations in a later feature PR |
| Required CI | `test`, `data-smoke`, `finance-smoke` passed at `214905b` | Require them again on each new head |
| Research conclusion | Cross-source benefit and faithful reproduction are unproved | Keep these gates open; complete controls, labels and ablations |

**First work session:** set up the PR branch, run the checks, obtain the private run artifacts listed below, and reproduce the completed eleven-batch cohort summary. Then follow the implementation order in the next-version plan. Follow [the next-version plan](VERSION2_PLAN.md) after retaining the current version’s open gates. Do not tune on this inspected cohort and later call it unseen evaluation data.

**Artifact transfer required:** a Git clone contains code and compact results, not raw predictions or private review records. Ask the owner for the five trace directories in `configs/demo.json`, `runs/version1/cohort-ai-audit-batch1.json` through `cohort-ai-audit-batch11.json`, and original review exports. Preserve relative paths and verify hashes. Share no API tokens or account credentials.

## 1. Read this first

The project investigates whether jointly selecting complementary web/API evidence improves complete evidence coverage and grounded answers under a fixed context budget.

The repository has working research infrastructure and several completed development experiments. **The full five-phase research roadmap is not complete.** An implemented module, a passed smoke test, and a demonstrated research improvement are different milestones.

The current adapted generator is Qwen2.5-1.5B-Instruct, rather than the original paper's model contract. The router uses keyword rules; selection support features are lexical proxies; reliability verification currently handles a narrow historical closing-price contract. No general cross-source benefit, held-out semantic accuracy improvement, or publication readiness has been established.

**The accepted-output AI audit is complete. The next engineering work is query-only answer contracts, conservative acceptance checks and live inference in the existing demo, followed by the open research gates.** Independent human evidence review remains an open scientific gate. AI-assisted assessments and successful provenance checks do not satisfy that gate.

Start with this file, then the [approved roadmap](../ROADMAP_REVIEW.md), [evaluation protocol](EVALUATION_PROTOCOL.md), and [prospective review protocol](PROSPECTIVE_EVALUATION.md). Older reports describe historical snapshots; use later reports for the work that supersedes them.

## 2. Phase tracker

| Phase | Intended outcome | Implemented and verified | Remaining completion gate | Status |
| --- | --- | --- | --- | --- |
| **1 — Feasibility and baseline** | Reproducible environment, real inputs, faithful baseline or explicit adaptations | Pinned upstream/dataset/assets; strict loader; BM25 and BGE retrieval pilots; original finance snapshot slice; guarded GPU generation | Original router/checkpoint, complete API backing data, generator/judge and paper configuration still unresolved | Engineering foundation complete; faithful reproduction blocked |
| **2 — Evidence selection** | Joint selection beats appropriate baselines at the same budget | Unified evidence schema; top-K, MMR, coverage-only, joint pair selection and bounded exact search; 25-question/125-context smoke and provenance verification | Reviewed support sets, evidence-completeness evaluation, genuinely cross-source cases and generated-answer comparisons | Implemented; scientific gate open |
| **3 — Adaptive routing** | Measured quality/cost trade-off against fixed and all-source retrieval | Three routing policies; shared budgets/date gates; 8,118 real-data plans; 150-answer development pilot with human review; six-question historical GPU comparison | Trained/calibrated router, source-necessity labels, broader reviewed evaluation and representative trade-offs | Development experiments complete; broader gate open |
| **4 — Reliability and hard evaluation** | Conflict handling, bounded retrieval, claim verification and reviewed evaluation | Comparable structured-price conflict checks; one-extra-lookup sufficiency loop; strict price-field verifier; actual bounded regeneration; fresh 50-question evidence-review workflow | Prospective human annotations; general web/cross-source claim verification; reviewed semantic outcomes; entity/event overlap audit | Bounded price implementation complete; general research gate open |
| **5 — Final validation and packaging** | Full ablations/statistics, defensible research report/paper, cited demo | Reproducible configs, manifests, review pages, 250-output verification, paired literal diagnostics and verified FastAPI/Next.js replay/retrieval explorer | Full semantic/coverage evaluation and ablations, final paper/report, live generation and claim-level citations | Final research/product phase not completed |

### Tracking checklist

- [x] Create repo and enforce feature-branch/PR/CI workflow.
- [x] Pin and validate real dataset and available original API snapshots.
- [x] Implement evidence selection and matched context costs.
- [x] Implement deterministic source routing and shared budgets.
- [x] Execute and verify adapted generation pilots on Kaggle.
- [x] Import human review of the first 50 generated development questions.
- [x] Execute date-compatible historical routing comparison.
- [x] Implement and measure bounded historical-price reliability.
- [x] Execute actual regeneration after missing evidence is retrieved.
- [x] Freeze 50 prospective questions and build evidence-review/export/import tooling.
- [ ] Import resolved human evidence decisions for the prospective packet.
- [ ] Audit entity/event overlap beyond URL/text checks.
- [x] Add an explicit-ID five-selector runner and complete 250-request tokenizer preflight (PR #16, pending merge).
- [x] Complete GPU generation and verify all 250 outputs (PR #16, pending merge).
- [x] Complete cohort AI source review: 250/250 responses across 50/50 questions reviewed; zero responses remain.
- [x] Build and verify the FastAPI/Next.js replay/retrieval explorer across 444 admitted records (PR #16).
- [ ] Complete live inference and claim-level citation verification for the demo.
- [x] Finish the separate AI-assisted legacy audit: complete for all 50 questions / 150 responses; historical/regeneration audits also complete; cohort source review is now complete.
- [ ] Establish genuine cross-source necessity and compare source-only controls.
- [ ] Extend reliability beyond the narrow historical-price contract.
- [ ] Complete full baselines, ablations, cost/coverage reporting and statistical analysis.
- [ ] Resolve faithful reproduction blockers or clearly retain an adapted-only scope.
- [ ] Produce a defensible final research report/paper and cited demo.

## 3. What is actually implemented

| Area | Main code | Behavior and practical limit |
| --- | --- | --- |
| Data and acquisition | [dataset.py](../src/ace_pruningrag/dataset.py), [fetch.py](../src/ace_pruningrag/fetch.py), [assets.py](../src/ace_pruningrag/assets.py) | Hash-verified assets; strict JSONL/bz2 validation; mixed scalar answer types handled; no silent row skipping |
| Inference boundary | `QueryInput` in `dataset.py` | Contains only identity, question, time and web sources; excludes gold answers, domain and release split labels |
| Evidence and retrieval | [evidence.py](../src/ace_pruningrag/evidence.py), [retrieval.py](../src/ace_pruningrag/retrieval.py), [learned_retrieval.py](../src/ace_pruningrag/learned_retrieval.py) | Exact source spans/IDs; deterministic BM25; adapted BGE-M3/reranker pilot |
| Selection | [selection.py](../src/ace_pruningrag/selection.py), [selection_experiment.py](../src/ace_pruningrag/selection_experiment.py) | Shared candidates and rendering costs; top-K/MMR/coverage/joint/exact search; exact search capped at 14 candidates and optimizes the configured objective, not evidence truth |
| Routing | [routing.py](../src/ace_pruningrag/routing.py), [routing_experiment.py](../src/ace_pruningrag/routing_experiment.py) | Fixed web, all available, heuristic adaptive; one shared budget; unavailable/unknown-date sources blocked; no calibrated probabilities |
| Original finance slice | [finance_api.py](../src/ace_pruningrag/finance_api.py), [daily_prices.py](../src/ace_pruningrag/daily_prices.py) | Verified original lookup assets; read-only daily-price SQLite; scalar-only deserialization; not a complete/live finance service |
| Historical requests | [historical_prices.py](../src/ace_pruningrag/historical_prices.py), [historical_comparison.py](../src/ace_pruningrag/historical_comparison.py) | Explicit single possessive ticker, previous calendar day's close; no trading-day backfill, same-day look-ahead or inferred currency |
| Generation | [generation.py](../src/ace_pruningrag/generation.py), [generated_driver.py](../scripts/generated_driver.py) | Pinned Qwen, greedy decoding, float32/logit guards, complete prompt/output budgets, actual output IDs and costs |
| Reliability | [reliability.py](../src/ace_pruningrag/reliability.py), [regeneration.py](../src/ace_pruningrag/regeneration.py) | Comparable price conflicts, bounded evidence retry, conservative price-answer verification, genuine second generation when dated evidence is absent |
| Review imports | [generated_reviews.py](../src/ace_pruningrag/generated_reviews.py), [reviews.py](../src/ace_pruningrag/reviews.py), [prospective.py](../src/ace_pruningrag/prospective.py) | Hash/provenance binding, attestation checks, duplicate rejection, immutable original exports and explicit unresolved counts |
| Execution and verification | [scripts](../scripts), [CI](../.github/workflows/ci.yml) | Private allowlisted Kaggle bundles; isolated inference dependencies; independent trace verifiers; three required CI jobs |

A local FastAPI/Next.js replay and fresh-retrieval explorer is implemented in PR #16; see [demo setup](DEMO.md). Live model inference and deployment remain unfinished. No general web claim extractor, trained router or full knowledge graph API is implemented yet.

## 4. Verified experiments and what they mean

### Foundation and selection

- RM3QA: **2,706 questions and 13,530 web pages**, five pages per question.
- BM25 smoke: first 25 real questions, reproduced locally and on Kaggle.
- BGE-M3/BGE-reranker pilot: five genuine questions; adapted retrieval only.
- Selector smoke: **25 questions × five methods = 125 verified contexts**. Lexical support proxies do not establish real complete-evidence coverage.
- Routing audit: **2,706 questions × three policies = 8,118 verified plans**. Only web was eligible, so plans showed no adaptive advantage.

### First 50 generated development questions

The accepted float32 run produced **150 answers over 50 distinct questions and three policies**. All policies had identical prompts and predictions because date-compatible API evidence was absent.

Per policy, the imported human review records:

| Correct | Incorrect | Abstained | Uncertain | Confirmed correct fraction |
| ---: | ---: | ---: | ---: | ---: |
| 13 | 23 | 12 | 2 | 26% |

The correctness bounds are 26–30%, depending on the two unresolved judgments. These are development reviewer results, not held-out accuracy. The 150 variants are not 150 independent questions. The earlier failed float16 run is excluded; retained artifacts document that failure.

See [generated pilot](PHASE3_GENERATED_PILOT.md), [human review](PHASE3_HUMAN_REVIEW.md), and [validation JSON](../results/phase3/generated_pilot/human_review_validation.json).

### Six historical closing-price questions

| Initial policy | Routed API calls across six questions | Raw generator abstentions |
| --- | ---: | ---: |
| Fixed web | 0 | 4/6 |
| All available | 6 | 1/6 |
| Adaptive | 4 | 3/6 |

Adaptive missed AEAE/TBMC closing-price phrasing. BLACW abstained even with API evidence. All policies had zero literal reference matches, which **does not mean zero semantic accuracy**: currency symbols, prose and numeric precision differ. These six cases are development data now.

See [price eligibility](PHASE3_PRICE_ELIGIBILITY.md) and [historical comparison](PHASE3_HISTORICAL_COMPARISON.md).

### Reliability and actual regeneration

| Initial policy | Strictly verified price-field answers before → after regeneration | Extra model calls |
| --- | ---: | ---: |
| Fixed web | 0/6 → 3/6 | 6 |
| All available | 3/6 → 3/6 | 0 |
| Adaptive | 1/6 → 3/6 | 2 |

The final run made **18 initial + 8 retry = 26 model calls**, used 29,568 input and 465 output tokens, and had a maximum cumulative reserved budget of 2,872 tokens. The limits were 2,048 tokens per round and 4,096 across two rounds. Two completed kernel versions consumed **52 total generations**; version 2 is the admitted implementation result.

All eight retry prompts/answers matched the direct all-source controls. On this set, direct all-source retrieval is cheaper than correcting a missed source with another generation. Price-field acceptance is not independent semantic accuracy. Dollar-denominated prose can be withheld because the snapshot does not establish currency; BLACW remains an abstention.

See [reliability replay](PHASE4_RELIABILITY.md), [bounded regeneration](PHASE4_BOUNDED_REGENERATION.md), and [results](../results/phase4/regeneration).

### Latest milestone: prospective review packet

- **50 prospective questions, 600 BM25 excerpts**, excluding 90 recorded pilot/audit IDs from nine artifacts.
- Duplicate question text and shared canonical source pages are excluded against prior cases and within the new set.
- Packet SHA-256: `324b5c35dc08ac43ce9c841f1a6a35086007badc8436b1d139f2fb01d3a80b33`.
- All source pages/candidate spans were reconstructed and verified. Altered source text and exclusion records were rejected.
- The frozen evidence packet itself made **zero model calls**. PR #16 now adds a separate 250-request generation experiment; its GPU job completed; all 250 outputs are verified, and AI source review is in progress. Independent human annotations remain pending.

This is prospective relative to documented pilots, not an independently sealed or fully entity/event-disjoint benchmark. It is web-only and cannot prove cross-source necessity. See [protocol](PROSPECTIVE_EVALUATION.md) and [frozen manifest](../results/evaluation/prospective_v1/manifest.json).

## 5. Repository map and pinned inputs

```text
configs/                 frozen assets and experiment protocols
src/ace_pruningrag/       reusable research implementation
scripts/                 GPU bundles, verifiers, review builders/importers
scripts/templates/       local review page templates
results/                 tracked compact summaries, hashes and manifests
docs/                    phase reports and experiment limitations
tests/                   schema, budgets, provenance and failure checks
data/                    ignored downloaded datasets/assets/weights
runs/                    ignored full traces, packets, exports and GPU outputs
.cache/                  ignored upstream/compatibility copies and temporary artifacts
```

| Input | Pin / location |
| --- | --- |
| RM3QA dataset | `fishsure/RM3QA` revision `f56a19b1348559be73b7ae4e4626d0d2ed778b21`; [dataset config](../configs/dataset.json); approximately 65 MB |
| Original upstream | `USTCAGI/PruningRAG` commit `cfae4e46e73144b07df84d7760f759e39db54062`; untouched checkout in `.cache/upstream/PruningRAG` |
| CRAG daily prices | Commit `ad1518887dd4d9ebcd7de95388c7a62751e7705c`; [price config](../configs/crag_prices.json); approximately 136 MB |
| Adapted generator | `Qwen/Qwen2.5-1.5B-Instruct` revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`; [generator config](../configs/generated_pilot.json); approximately 3.1 GB of weights |
| BGE tokenizer | Pinned revision/asset checksum in [selection config](../configs/selection_smoke.json) |

A clone does **not** include raw data, full GPU traces, weights, human exports, credentials or local review pages. Compact result hashes are not substitutes for the full traces needed by verifiers. Ask the owner for an approved transfer of required run artifacts, recover accessible private Kaggle outputs, or reproduce the run with its pinned config.

Existing GPU kernels use the owner's `ionrey` Kaggle account and are private. Your own Kaggle identity/authentication is needed for new jobs unless the owner arranges access. Do not assume the friend's account can download the owner's private outputs. Credentials stay outside the repository.

The owner's local checkout is `/Users/manoharpaturi/Desktop/rag`. Existing useful local artifacts include:

- `runs/kaggle/generated-output-v3/phase3-pilot/generated/` — accepted first-50 generation trace.
- `runs/kaggle/historical-output-v1/phase3-pilot/` — initial historical diagnostic.
- `runs/kaggle/regeneration-output-v2/phase3-pilot/` — admitted regeneration run.
- `runs/phase3/generated-human-review-import-v1/` — preserved first-50 human export/import.
- `runs/evaluation/prospective-v3/packet.json` and `review.html` — current prospective packet.

These paths describe the owner's machine, not files available automatically on a fresh clone.

## 6. Contributor setup and checks

Use Python 3.12 and `uv`. The owner's 8 GB Apple Silicon Mac is for development/tokenizer checks; recorded generation runs use Kaggle Tesla T4 GPUs. Keep `--no-editable`: this checkout encountered macOS Finder-hidden `.pth` behavior with editable installs.

For a friend without write access, fork first using their own GitHub account:

```bash
gh repo fork ManoharPaturi/ace-pruningrag --clone
cd ace-pruningrag
uv sync --locked --no-editable --extra demo --python 3.12
uv run --locked --no-editable ruff check src tests scripts
uv run --locked --no-editable ruff format --check src tests scripts
uv run --locked --no-editable --extra demo pytest -q
```

The current owner workspace has **138 passing tests with the demo extra** (recorded implementation checkpoint). This includes the PR abstention-consistency test; it is not the merged-main test count. All three required CI jobs passed on PR #16 verified implementation head `214905b` (before this documentation update); CI must pass again on each new PR head. CI additionally runs real dataset/finance/tokenizer checks; passing unit tests alone is insufficient.

Download data and run a small retrieval check, using a new output directory:

```bash
uv run --locked --no-editable ace-rag fetch-data
uv run --locked --no-editable ace-rag smoke --output runs/friend/bm25-v1
uv run --locked --no-editable python scripts/verify_smoke.py --run runs/friend/bm25-v1
```

Optional original price checks:

```bash
uv run --locked --no-editable python scripts/prices_smoke.py \
  --output runs/friend/prices-v1.json
uv run --locked --no-editable --extra generation python scripts/generated_preflight.py \
  --output runs/friend/generated-preflight-v1
uv run --locked --no-editable --extra generation python scripts/historical_preflight.py \
  --retry --output runs/friend/historical-preflight-v1
```

Preflight downloads tokenizer/config sidecars rather than the generator's large weight file. A full GPU bundle fetches the weights and must be treated as a separate compute run.

The upstream audit intentionally exits 2 when reproduction remains blocked/not ready; read the written audit rather than interpreting that exit as an unexplained crash. Most experiment/import directories refuse overwriting. Always choose a fresh versioned output name.

## 7. Resume the current review gate

On a fresh clone, rebuild the same frozen packet:

```bash
uv run --locked --no-editable ace-rag fetch-data
uv run --locked --no-editable python scripts/prospective_evaluation.py freeze \
  --output runs/friend/prospective-v1
uv run --locked --no-editable python scripts/prospective_evaluation.py verify \
  --packet runs/friend/prospective-v1/packet.json \
  --output runs/friend/prospective-verified-v1
uv run --locked --no-editable python scripts/build_evidence_review.py \
  --packet runs/friend/prospective-v1/packet.json \
  --output runs/friend/prospective-v1/review.html
uv run --locked --no-editable python -m http.server 8050 \
  --bind 127.0.0.1 --directory runs/friend/prospective-v1
```

Open `http://127.0.0.1:8050/review.html`. The owner's existing review URL was `http://127.0.0.1:55380/review.html`; that localhost address only works on the owner's machine while its server is running.

For each question, write required facts, inspect evidence, choose supported/missing/uncertain, enter alternative complete support sets (e.g. `1,3; 2,5`), and attest only to actual inspection. Preserve hard/negative/ambiguous cases. An insufficient top-12 pool does not prove no answer exists in the full corpus. Export decisions; drafts/partial reviews remain unresolved.

Import the actual exported file, substituting its path:

```bash
uv run --locked --no-editable python scripts/prospective_evaluation.py import \
  --packet runs/friend/prospective-v1/packet.json \
  --export /absolute/path/to/ace-prospective-evidence-review.json \
  --output runs/friend/prospective-human-review-v1
```

Keep the original export/import private. Publish only appropriate compact validation summaries through a PR. A validated import still does not establish semantic answer accuracy, general cross-source necessity or publication readiness.

## 8. Ordered continuation plan

| Priority | Next action | Acceptance criterion |
| --- | --- | --- |
| **P0** | Reproduce environment, current checks and prospective packet | Unit/lint checks pass; packet hash matches the frozen manifest; raw assets remain pinned |
| **P1** | Obtain and import independent human candidate-evidence review | Attested resolved requirements/support sets; unresolved questions explicitly reported; original export preserved |
| **P2** | Audit entity/event overlap and freeze a fresh evaluation protocol | Record residual overlap and any exclusions/version changes; freeze model, query IDs, candidates, budgets, methods, prompts and scoring before execution |
| **P3** | Reproduce the completed PR #16 source audit and implement query-only acceptance checks | Same frozen IDs/candidate pools/generator/budget; all 250 outputs verified; AI and human scoring kept separate; no gold/support-set leakage |
| **P4** | Build genuine cross-source evaluation and general reliability components | Reviewed source-only sufficiency/necessity controls; comparable conflicts and dated claims; independently measured ablations |
| **P5** | Package final results and demo | Paired uncertainty estimates, semantic/support/abstention/coverage/cost metrics, retained negative results, evidence-backed report and traceable demo citations |

**Runner status:** PR #16 implements `configs/cohort_evaluation.json`, `src/ace_pruningrag/cohort.py` and `scripts/cohort_driver.py`. It uses the 50 explicit frozen IDs rather than the first 50 file-order records. Main’s older `generated_pilot` and `selection-smoke` do not substitute for this cohort. Use the PR branch until the owner merges it. The current run is exploratory and AI-assisted; inspected questions become development data for future tuning.

Keep tuning on earlier development data. Reviewed support sets are evaluation inputs; only an explicitly labeled oracle diagnostic may use them. The existing exact selector optimizes its configured objective and is not a gold-evidence oracle automatically.

Useful development follow-ups include the adaptive router's missed closing-price phrases and BLACW's remaining abstention. Treat fixes as separate ablations with retained controls; these inspected six cases cannot become a new held-out benchmark.

## 9. Branch, PR and research rules

The repository is public. At the verified snapshot, only `ManoharPaturi` has direct repository write/admin access. Other contributors can fork, push branches in their forks, and raise PRs.

- **Only the owner merges main.** Do not directly push/commit to main or merge the PR on the owner's behalf.
- Required checks: `test`, `data-smoke`, `finance-smoke`; strict up-to-date checks and protection enforcement for administrators are enabled.
- Required review count is currently zero because there is no second repository writer; that is not a grant of merge access to public contributors.
- Preserve the original roadmap, source snapshots, failed/superseded runs and existing exports.
- Do not commit raw data, weights, full traces, review notes or credentials. Commit reproducible scripts/configs and compact hashes/results.
- Never use gold answers, domain labels, release split values or human support sets in real inference. Do not guess what release split values mean.
- Do not call heuristic scores probabilities, synthetic fixtures research observations, numeric support semantic accuracy, or repeated policy variants independent questions.
- Record all retrieval/preflight/validation/generator/judge calls and complete prompt/output budgets. Per-round matched budgets do not imply matched cumulative costs after retry.
- Keep upstream source separate. Upstream redistribution/reuse terms remain unresolved; avoid copying unlicensed implementation code into this repo.

## 10. Merged work and update log

| PRs | Delivered work |
| --- | --- |
| #1–#2 | Foundation, pinned data/upstream audit, Kaggle bootstrap, deterministic BM25 |
| #3–#5 | Guarded compatibility copy, original finance slice, BGE retrieval and isolated GPU dependencies |
| #6 | Unified evidence selection and matched-cost smoke |
| #7 | Routing/shared budgets and initial human draft-review imports |
| #8–#9 | Guarded actual generation, independent verification and first-50 human review |
| #10–#11 | Date-eligibility audit, prior-day price adapter and historical routing comparison |
| #12 | Bounded historical reliability and component replay |
| #13 | Actual evidence-triggered regeneration, costs, verifiers and review packet |
| #14 | Prospective 50-question freeze and human candidate-evidence review tooling |
| #15 | Contributor phase tracker and handoff |
| #16 (draft/open) | Explicit five-selector runner; completed/verified 250-answer GPU run; paired literal diagnostics; complete prior-run AI audits; partial cohort audit; verified replay/retrieval demo |

After each accepted milestone, update the phase table/checklist, verified main commit, test/check status, result links, open gates and next action. Record the PR and date. Never tick a research gate merely because its code merged.


## 11. Exact handoff: current work, next commands and acceptance gates

### Read and transfer these first

Read [current-version completion audit](VERSION1_COMPLETION_AUDIT.md) and [next-version plan](VERSION2_PLAN.md). They are PR #16 documents, not merged-main claims. Earlier dated audit batches describe partial progress. Legacy first-50 review is complete; the cohort progress file still records partial coverage.

| State | Files / artifact | What the friend must know |
| --- | --- | --- |
| Pushed PR #16 code | `configs/cohort_evaluation.json`, `src/ace_pruningrag/cohort.py`, `scripts/cohort_driver.py`, `scripts/cohort_preflight.py`, `scripts/verify_cohort.py`, `scripts/cohort_metrics.py`, `src/ace_pruningrag/response_audit.py` | Explicit cohort selection/generation, verification, paired literal diagnostics and review provenance validation exist; execution/results remain separate gates |
| Preflight complete | [local preflight](../results/version1/cohort/local_preflight.json) | 50 questions, 250 prepared requests, maximum reserved tokens 2,036; **zero actual generation calls** |
| Submitted GPU bundle | [bundle manifest](../results/version1/cohort/submitted_bundle_manifest.json), owner’s `runs/kaggle/cohort-kernel-v1/` | Private kernel `ionrey/ace-pruningrag-prospective-selectors`, version 1; live status COMPLETE, no failure message; all 250 outputs verified |
| Legacy verification | [generation verification](../results/version1/legacy_generation_verification.json), [human validation](../results/version1/legacy_human_validation.json) | All 150 accepted development outputs and 150 original human records revalidated; two question-level human judgments remain uncertain |
| PR audit progress | [review progress](../results/version1/legacy_review_progress.json), [AI audit validation](../results/version1/legacy_ai_audit_validation.json) | Nine AI review batches cover all 50 distinct questions / 150 responses; historical and regeneration audits are also complete |
| PR code/test | `src/ace_pruningrag/response_audit.py`, `tests/test_response_audit.py` | Added rejection of an abstention verdict that contradicts actual answer text; covered by the 138-test workspace check |
| Private audit records | owner’s `runs/version1/legacy-ai-audit-batch1.json` through `legacy-ai-audit-batch9.json` | Must be transferred with the exact original predictions trace to reproduce audit validation; these are ignored and absent from Git |

The audit progress and validation changes have been preserved in this PR update. Do not discard other local changes when continuing. A branch push does not include ignored run artifacts. Transfer the full relevant directories through an owner-approved private channel, without credentials. Preserve hashes and original human exports; do not silently replace judgments with AI assessments.

### Get the pending implementation

After forking/cloning as in section 6, fetch the owner’s PR branch into your own working branch:

```bash
git remote add upstream https://github.com/ManoharPaturi/ace-pruningrag.git
git fetch upstream
git switch -c codex/continue-version1 upstream/feat/prospective-selector-evaluation
uv sync --locked --no-editable --extra demo --python 3.12
uv run --locked --no-editable --extra demo pytest -q
uv run --locked --no-editable ruff check src tests scripts
uv run --locked --no-editable ruff format --check src tests scripts
```

If `upstream` already exists, inspect `git remote -v` and use it rather than adding it again. Review the PR diff and recover the ignored private artifacts before validating historical audit records. Owner merging PR #16 changes the base: fetch again and use the latest main for subsequent PRs.

### Reproduce the completed cohort verification

First reproduce the tokenizer-only preflight with a fresh output directory:

```bash
uv run --locked --no-editable ace-rag fetch-data
uv run --locked --no-editable --extra generation python scripts/cohort_preflight.py \
  --output runs/friend/cohort-preflight-v1
```

The contract is five selectors (`top_k`, `mmr`, `coverage`, `joint`, `exact`), 12 shared candidates, at most five selected excerpts, pinned Qwen2.5-1.5B-Instruct, greedy seed 42, 96 output tokens, 2,048 total request tokens and 250 verified generations. Groups/conflicts are disabled and support is a query-term proxy. This tests the configured selector objective, not genuine evidence complementarity.

The existing version-1 job completed and all outputs were downloaded and verified. Reuse its artifacts. For reproduction, use authenticated Kaggle access arranged by the owner and confirm the version before downloading; do not launch a duplicate:

```bash
uv tool run --from kaggle==2.2.4 kaggle kernels status ionrey/ace-pruningrag-prospective-selectors
```

Download the completed version into a fresh directory and inspect its structure. Expected output layout is `cohort-pilot/generated`:

```bash
uv tool run --from kaggle==2.2.4 kaggle kernels output \
  ionrey/ace-pruningrag-prospective-selectors -p runs/friend/cohort-output-v1
uv run --locked --no-editable --extra generation python scripts/verify_cohort.py \
  --run runs/friend/cohort-output-v1/cohort-pilot/generated \
  --output runs/friend/cohort-verification-v1.json
uv run --locked --no-editable python scripts/cohort_metrics.py \
  --run runs/friend/cohort-output-v1/cohort-pilot/generated \
  --output runs/friend/cohort-metrics-v1.json
```

Verification must cover all 250 predictions, 50 matched question groups, frozen source spans, source/protocol hashes, reconstructed prompts/selections, output decoding and full budgets. Metrics provide paired literal-agreement/abstention diagnostics with 10,000 bootstrap samples, seed 42; they do not establish semantic accuracy. Retain failures and uncertainty.

If the existing job cannot be accessed, agree on ownership of a replacement run before submitting it under the friend’s account. Build using `scripts/build_kaggle_kernel.py --mode cohort --owner FRIEND_KAGGLE_USERNAME --output runs/friend/cohort-kernel-v1`, retaining the same protocol and recording the new version. The owner’s credentials must not be shared.

### Remaining implementation order

1. Reproduce validation of the complete 50-question / 150-response legacy AI source audit after obtaining the nine private batches and exact trace. Keep AI judgments separate from original human decisions; validate binding without treating it as independent semantic proof.
2. Continue the source-bound audit of the already verified 250-response experiment: all 250 responses are reviewed. Audit each actual answer and its evidence before publishing semantic claims; do not rerun the completed kernel. Historical 18-output and regeneration 26-call traces are now freshly verified and AI-assessed; recover their three private audit files for reproduction. Do not extend this claim to failed/superseded kernels.
3. Obtain independent evidence/answer review, audit entity/event overlap and resolve ambiguous references. AI inspection does not close this gate.
4. Establish genuine cross-source cases with reviewed atomic requirements and source-only controls. Generalize entity/date/unit verification and measure all extra retrieval/model calls.
5. Complete missing baselines and ablations, paired quality/coverage/cost analysis, evidence-backed report and live inference with claim-level citations in the existing FastAPI/Next.js explorer. Resolve original reproduction artifacts or retain an explicit adapted-only scope.
6. Finalize the next-version plan from observed failures, using a fresh evaluation cohort that excludes all inspected/tuned-on questions. Keep unfinished current-version gates visible.

**Done means:** code works, exact traces and costs are verified, review provenance is preserved, required CI passes, limitations/results are documented, and the owner has reviewed and merged the PR. Research completion additionally requires the open scientific gates in section 2. A queued job or merged feature alone is not a completed phase.


### Earlier accepted-run audit checkpoint

The historical and regeneration verification and AI inspection are complete: [44-record audit](../results/version1/historical_regeneration_ai_audit.json), [historical verification](../results/version1/historical_reverification.json), [regeneration verification](../results/version1/regeneration_reverification.json). Total inspected accepted response records are 194, across 50 legacy questions and six historical questions with repeated controls/retries. This is not an independent 194-case benchmark.

Transfer `runs/version1/historical-ai-audit-v1.json`, `regeneration_initial-ai-audit-v1.json` and `regeneration_retry-ai-audit-v1.json` with the exact original traces. All eight retries matched direct all-source controls; dollar-denominated answers remain uncertain where currency metadata is absent. BLACW remains an abstention with an available numeric field. The 250-response run is verified; source review is still incomplete. Scientific and live-generation demo gates remain open.


### Local demo handoff

The [FastAPI/Next.js explorer](DEMO.md) now builds and its browser flow is verified for recorded answers, exact source provenance and fresh BM25 retrieval. Live local URLs are API `http://127.0.0.1:8060` and UI `http://127.0.0.1:3060` while the owner’s processes are running. These addresses do not provide remote access. Clone and start both services using the documented commands. Required CI now includes the web production build; backend tests require `--extra demo`. The full demo gate still needs live generation and the remaining research requirements.


### Earlier partial cohort checkpoint — 13 October

All 250 outputs from the existing version-1 kernel are downloaded and verified. Read [selector results](COHORT_SELECTOR_RESULTS.md) and `results/version1/cohort/verification.json`, `paired_metrics.json`, `gpu_summary.json`, and `ai_review_progress.json`. One hundred fifteen responses across 23 questions are AI source-reviewed; 135 remain. The explorer now admits all 444 verified accepted response records, while AI semantic review coverage is 309 records (194 prior plus 115 cohort). Do not confuse trace verification with complete semantic review. Raw new artifacts are in `runs/kaggle/cohort-output-v1/cohort-pilot/generated/` and eleven private review batches are `runs/version1/cohort-ai-audit-batch1.json` through `cohort-ai-audit-batch11.json`.

### Validate the completed cohort review

After receiving the exact private trace and eleven existing batches, run from the repository root:

```bash
uv run --locked --no-editable python - <<'PYTHON'
import json
from pathlib import Path
from ace_pruningrag.response_audit import validate_ai_audits

trace = Path("runs/kaggle/cohort-output-v1/cohort-pilot/generated/predictions.jsonl")
batches = sorted(Path("runs/version1").glob("cohort-ai-audit-batch*.json"))
if not batches:
    raise FileNotFoundError("Obtain the owner's existing audit batches first")
print(json.dumps(validate_ai_audits(batches, trace), indent=2))
PYTHON
```

At the current checkpoint the expected result is 250 reviewed / zero unreviewed, with `full_ai_response_audit_complete: true`. Earlier partial batches remain preserved. This validates response binding, not semantic truth. For each unreviewed `(interaction_id, policy)`, read the complete answer and its actual selected excerpts. Record semantic correctness separately from whether the supplied evidence supports the claim; preserve uncertainty and prose abstentions. Append a fresh batch without overwriting prior notes. Keep `reviewer_type: AI` and `human_validated: false` for AI judgments. External fact checks are review evidence, never additions to the frozen generation input.

After each batch, rerun validation, update [cohort review progress](../results/version1/cohort/ai_review_progress.json), [selector findings](COHORT_SELECTOR_RESULTS.md), [completion audit](VERSION1_COMPLETION_AUDIT.md) and this tracker. Private batch notes remain ignored. Publish compact counts/hashes and reproducible code through a PR. At 250/250 AI reviews, mark only the AI audit complete; independent human labels and the remaining scientific gates still need their own evidence.

### Handoff update — 13 October 2026

Confirmed live: main is `ba30586`; PR #15 is merged; PR #16 is draft/open at implementation head `214905b`; all required checks passed. Main protection requires strict checks and applies to administrators. This update corrects earlier pending-run instructions and records the current review/demo progress. Feature changes and this document belong to PR #16 until the owner merges it.


### Current owner-led continuation checkpoint

The owner has asked the assistant to continue implementation; a friend handoff is no longer required for progress. All 444 admitted accepted outputs are now AI-audited; the cohort is 250/250 across 50 questions with eleven batches. See [the completed cohort audit](COHORT_RESPONSE_AUDIT.md) and [next implementation priorities](VERSION2_PLAN.md). Earlier partial checkpoint counts below/above are historical; use the current compact progress file and completed report. There are 138 passing local tests. Independent human/scientific and live-generation requirements remain open.


### Retained output inventory checkpoint

All ten declared local prediction paths have bound AI assessments; see [retained audit](RETAINED_RESPONSE_AUDIT.md), `configs/retained_audits.json`, and `results/version1/retained_trace_audit.json`. Eight distinct file hashes contain 620 records; a second 26-record download brings stored-path accounting to 646. Only 444 records remain admitted. Transfer the three private excluded/superseded audit files named in the report to reproduce this check. Local tests now total 147. Live inference, general reliability and scientific gates remain open.
