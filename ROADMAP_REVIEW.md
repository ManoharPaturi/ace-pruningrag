# ACE-PruningRAG: proposed implementation plan

Prepared 9 October 2026. Approved by the user on 9 October 2026. The private repository is `ManoharPaturi/ace-pruningrag`; Phase 1 implementation has started. Kaggle was subsequently selected as the remote GPU target. The findings below record the initial review unless explicitly updated.

## Recommendation

Keep the project's objective and all five phases, but test the main contribution earlier: selecting complementary evidence across web and API sources under a fixed context budget. Add routing, dynamic budgets, retrieval loops, and verification in separate experiments after this contribution has been measured.

The central hypothesis is that joint selection improves complete supporting-evidence coverage and grounded answer quality compared with independent relevance ranking at the same token budget. This remains a hypothesis; the review does not establish novelty, effectiveness, or publication readiness.

## Verified starting state

- The workspace contains the original 12-page roadmap PDF and was not a Git repository when inspected.
- GitHub CLI authentication is active as `ManoharPaturi`.
- Proposed new repository: `ManoharPaturi/ace-pruningrag`, private initially. No matching name appeared in the 100 repositories returned by the availability check; creation must still handle a name collision.
- This local machine is Apple Silicon with 8 GiB RAM. Use it for development, data validation, cached retrieval analysis, and small smoke tests. Plan remote GPU compute for faithful large-model experiments; model substitution must be disclosed as an adapted baseline.
- The paper's arXiv record states CIKM 2025 acceptance. Its version 4 includes the conference proceedings DOI.
- Upstream code inspected at commit `cfae4e46e73144b07df84d7760f759e39db54062`.
- `main.py:159` passes an additional `noise` positional argument absent from `Retriever.__init__` in `models/retrieve/retriever.py:24`. Static inspection indicates a constructor mismatch; no runtime reproduction has been attempted.
- The upstream main script defaults to CUDA and hardcodes local mock API and selection-model services. The README mentions router weights, but no `models/router` path appeared in the current repository tree. Check artifact availability before promising exact reproduction.
- Hugging Face's RM3QA viewer reports a mixed number/string type error in `alt_ans`. This is a viewer/loader compatibility finding, not proof that the raw JSON records are invalid.
- RM3QA exposes a 5-web compressed file of 64,803,084 bytes and a 50-web compressed file of 755,635,711 bytes. Use the small variant for smoke tests; lock the appropriate variant for the target paper experiment and do not compare variant changes as method improvements.
- GitHub reports no detected upstream code license and the inspected tree contains no license file. The dataset page separately lists Apache 2.0. Keep the new implementation separate, reference the pinned upstream checkout, and resolve code reuse terms before redistributing upstream source.

## Proposed changes and reasons

### 1. Add a reproduction feasibility check

Audit imports, constructor signatures, model/checkpoint access, mock API server and backing data, dependency compatibility, dataset schema, evaluator, and target paper configuration. Keep upstream untouched in a separate checkout. Record necessary compatibility patches separately with their behavioral impact.

Distinguish three outcomes: environment smoke test; reproduction of the released pipeline; replication of reported paper results. Success in one does not prove the next. If artifacts are unavailable, explicitly record the blocker and label substitute runs as adapted baselines.

### 2. Move evaluation design into the first phase

Freeze dataset revisions, query IDs, corpus snapshots, prompts, generator and judge versions, seed lists, token budgets, and scoring definitions before method tuning. Define development and held-out evaluation splits with entity/event grouping where practical to limit leakage.

Inspect whether RM3QA supplies supporting-evidence annotations before claiming Recall@K, MRR, or CompleteEvidence metrics. For the extension, annotate requirements and acceptable evidence sets; alternative valid sources must count as support rather than requiring a single arbitrary chunk ID.

Start with approximately 50-100 human-reviewed pilot questions spanning single-source, genuine cross-source, distractor, missing-evidence, conflict, and temporal cases. Include source provenance and reviewer decisions. Scale toward 200-500 only when the annotation process is reliable and resources permit. Assisted drafts are not independently verified labels.

Confirm true cross-source necessity by testing whether either source alone can support the answer. A question mentioning two sources is insufficient evidence of that property.

### 3. Test the core selector before changing routing

Implement the unified evidence schema and selector with fixed routing, the same candidate evidence pool, the same generator, and matched context budgets. Compare independent top-K, MMR (relevance balanced against redundancy), coverage-only selection, and joint complementary selection. Include small-pool oracle selection as a diagnostic upper bound when annotated evidence is available; keep oracle labels out of the real method.

Formalize the roadmap's score as an implementable objective, for example:

`maximize F(E; q), subject to sum(token_cost(e) for e in E) <= B`

Here `q` is the question, `E` the selected evidence set, and `B` the context-token limit. Define relevance, predicted requirement coverage, complementarity, redundancy, and compatible conflicts on a common scale. Tune weights on development data only. Gold answers and gold supporting-evidence labels are evaluation information, not inference inputs.

Complementarity must reflect whether evidence items jointly satisfy missing answer requirements. Different source names or low text similarity alone do not prove complementarity. A greedy selector may miss pairs whose value appears only together; compare pair/bundle additions and exact small-pool search before choosing the approximation. Do not claim optimization guarantees without checking the objective's assumptions.

Treat agreement cautiously: repeated copies of one claim are not independent confirmation, and differences in time, units, or definitions are not automatically contradictions. Compare like-for-like claims with provenance. A newer source is not automatically correct for a historical question.

### 4. Add adaptive retrieval and reliability as measured extensions

Only after the selector comparison, add multi-label routing and dynamic budgets. Establish source labels and held-out calibration before interpreting classifier scores as probabilities. Use deterministic/simple policies as initial baselines; train only with available labels and a separate development split.

Then add conflict handling, sufficiency-controlled re-retrieval, and claim verification independently. A rule-based coverage score should be called a score, not a calibrated probability. Cap total retrieval rounds and count all routing, extraction, verification, and judge calls in cost reports. Show answer accuracy, unsupported-claim rate, and answer coverage together so abstaining on everything cannot look successful.

Use NetworkX only when relations help selection or analysis. Keep graph features optional and prove their value with an ablation. Keep unresolved conflict status visible instead of rewarding majority agreement.

### 5. Make evaluation stronger and implementation smaller

Report two comparisons: selection-only on identical candidates, and end-to-end retrieval at matched total budgets. Record candidate retrieval cost separately from final context size. Report paired confidence intervals over the same query IDs, repeated seeds where relevant, category-level results, and improved as well as degraded cases.

Keep the original evaluator's accuracy, miss, hallucination, and score definitions for baseline reporting; additional grounding metrics are separate. Pin and cache judge decisions and human-audit a representative subset. A model judging its own answer is insufficient independent evidence.

Start with a Python package, command-line experiment runner, local files/SQLite, and the published retrievers. Add DuckDB if structured queries need it and a vector database if scale requires it. Defer FastAPI and Next.js until the research pipeline is stable.

Adaptive retrieval and context sufficiency already have published precedents. Position the contribution narrowly and perform a fuller related-work review before claiming novelty. Relevant starting points include Adaptive-RAG, Sufficient Context, MMR, and current routing benchmarks.

## Revised five-phase sequence

| Phase | Work | Completion gate |
| --- | --- | --- |
| 1: Feasibility, protocol, and baseline | Pin upstream; validate dataset/API/checkpoints; document compatibility patches; freeze evaluation; run a small baseline pilot and then the target baseline | Raw inputs, environment, prompts, predictions, traces, and metrics are recorded; unavailable reproduction assets are explicitly identified |
| 2: Main evidence-selection contribution | Unified schema; independent top-K, MMR, coverage-only, and joint selection at matched budgets | Held-out evidence completeness and grounded answer comparisons are available with failure analysis; neutral or negative results are retained |
| 3: Adaptive retrieval | Source routing and dynamic per-source budgets, tested separately and together | Measured quality/cost trade-off against fixed routing and all-source retrieval; no hidden budget increase |
| 4: Reliability and hard evaluation | Conflict module; bounded sufficiency loop; claim verification; reviewed evaluation extension | Component ablations, supported-claim and abstention/coverage metrics, reviewer records, and cost accounting are available |
| 5: Final validation and packaging | Full baselines/ablations; statistical analysis; paper draft; FastAPI/Next.js demo | Reproducible artifacts support the stated claims; demo citations trace to evidence; resume numbers come from completed experiments |

## Repository plan after approval

Create a fresh private GitHub repository named `ace-pruningrag` under the authenticated account. Keep the original roadmap alongside this approved review. Suggested initial structure:

```text
docs/                  roadmap, protocol, reproduction notes, related work
src/ace_pruningrag/     dataset, evidence, retrieval, selection, generation, evaluation
configs/               baseline and experiment configurations
scripts/               setup checks and experiment entry points
tests/                 meaningful schema, provenance, budget, and evaluator checks
results/               small tracked summaries and manifests
apps/                  added when the research pipeline is stable
```

Ignore credentials, raw datasets, model weights, large caches, and generated traces by default; retain scripts and hashes needed to recover them. Reference upstream by URL and immutable commit, with a separate checkout and compatibility patch record. Preserve upstream attribution and resolve reuse terms before copying its code into the new repository.

The first implementation milestone is Phase 1's setup audit, validated data loader, experiment configuration, and a small baseline run when the required services are available. A costed compute plan must precede paid experiments; no paid run or large-model download is part of this review.

## Sources inspected

- Original roadmap: `ACE_PruningRAG_5_Phase_Research_Roadmap.pdf` in this workspace.
- Base paper: https://arxiv.org/abs/2409.13694 and https://arxiv.org/html/2409.13694v4
- Official code: https://github.com/USTCAGI/PruningRAG
- Pinned main script: https://github.com/USTCAGI/PruningRAG/blob/cfae4e46e73144b07df84d7760f759e39db54062/main.py
- Pinned retriever: https://github.com/USTCAGI/PruningRAG/blob/cfae4e46e73144b07df84d7760f759e39db54062/models/retrieve/retriever.py
- Dataset: https://huggingface.co/datasets/fishsure/RM3QA
- Dataset file metadata: https://huggingface.co/api/datasets/fishsure/RM3QA/tree/main?recursive=true
- Adaptive-RAG: https://arxiv.org/abs/2403.14403
- Sufficient Context: https://arxiv.org/abs/2411.06037
- MMR context: https://www.cs.cmu.edu/~pbennett/papers/ICML-MLIR-Tutorial.pdf
- RAGRouter-Bench, a related-work lead rather than an evaluated baseline here: https://arxiv.org/abs/2602.00296

## Approval scope

Approval of this proposal authorizes creation of the new private repository and beginning Phase 1 under this sequence. It does not establish that experiments have succeeded or that the project is ready for publication.
