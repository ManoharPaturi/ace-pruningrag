# Phase 1 reproduction report

Date: 9 October 2026. Status: development infrastructure and real-data retrieval smoke completed; full published baseline reproduction is blocked.

## Completed

- New private GitHub repository and feature-branch/PR workflow. Empty `main` provides the first PR base and contains no implementation.
- Python 3.12 package and locked development dependencies. Runtime research infrastructure uses the standard library.
- PruningRAG preserved as a clean, detached upstream checkout at `cfae4e46e73144b07df84d7760f759e39db54062`.
- Hash-verified small RM3QA release at dataset revision `f56a19b1348559be73b7ae4e4626d0d2ed778b21`.
- All 2,706 records validated, with 13,530 web pages and no empty pages. Every record has five web pages.
- Answer types: 2,700 strings and 6 integers. Alternate answers: 67 strings, 48 integers, and 1 float. The independent loader accepts these scalar types without altering raw values.
- Release split values: 1,371 rows labeled 0 and 1,335 labeled 1. Their development/test semantics are not inferred.
- No `kg_info`, `kg_infos`, `api_results`, `supporting_facts`, or `evidence_ids` fields occurred in the downloaded variant. A compatible API server/snapshot is needed for original structured retrieval. Evidence completeness labels require a reviewed extension.
- First 25 real records passed an independent BM25 retrieval smoke. Mean candidate count 72.12; 3 selected chunks per query; mean context size 575.2 whitespace words; maximum 600 words. These are retrieval plumbing measurements, not model-quality results.
- Independent trace verification checked query IDs, original source character spans, source URLs, word counts, absence of gold answer fields, and context limits.
- 25 local tests passed. Lint and formatting passed. CI runs these checks and a separate real-data smoke job.
- Main-branch protection requires PRs and the `test`/`data-smoke` checks, with enforcement for administrators.
- Private Kaggle bootstrap completed as `ionrey/ace-pruningrag-phase1-bootstrap`, version 1. Downloaded artifacts confirm two Tesla T4 GPUs (15,636,037,632 bytes each), CUDA 12.8, PyTorch 2.11.0, and Python 3.13.15. Arithmetic smoke passed on both GPUs.
- Kaggle validated all 2,706 records and completed the same 25-query retrieval smoke. The downloaded source-bundle manifest matches the submitted allowlisted bundle. All selected evidence matches the committed-source local run, and remote trace spans/budgets were independently verified against local pinned raw data.
- The checked-in local smoke manifest now points to implementation commit `6d6d1644f75516f90fca5807608ccaa714a75623`. Earlier development traces remain preserved in ignored run directories.

## Confirmed reproduction blockers

| Finding | Evidence | Action before baseline run |
| --- | --- | --- |
| Retriever constructor mismatch | `main.py:159` passes 11 positional arguments; constructor at `models/retrieve/retriever.py:24` accepts 10 | Prepare and document a compatibility patch outside the clean checkout; decide the intended behavior of the unmatched noise argument |
| Domain-router adapter absent from checkout | Code refers to `models/router/domain`; directory is absent | Obtain the original adapter and record checksum; a replacement router is an adapted experiment |
| Model/tokenizer artifacts absent locally | Llama 3.1, BGE-M3, BGE reranker, and MiniLM paths are referenced | Resolve exact checkpoints and access, then provision on Kaggle |
| API service and backing data unverified | Local service ports 8000/8001/8002 have no listener; downloaded RM3QA variant has no API-response fields | Validate the compatible CRAG mock API server and historical snapshot, plus actual model endpoints |
| Paper configuration unresolved | Released defaults differ from README, including retrieval/chunk settings | Map one target paper result to exact models, dataset variant, prompts, pruning, and evaluator |

The upstream Python files parse successfully and local module imports resolve by static inspection. Missing model artifacts and services remain separate runtime issues. No large upstream dependencies were installed locally and no upstream model code was executed.

The released `RAGModel` loads its domain router even with the default web knowledge-source argument. An API generator alone will therefore not make this pipeline runnable. The README mentions a Dynamism Router, but the inspected tree supplies no router checkpoint directory; reproducing that behavior also requires resolving the release/paper gap.

## Metrics and limits

No answers were generated. No model judge ran. Answer accuracy, evidence recall, complete-evidence coverage, and token counts remain null. Zero LLM calls and zero paid inference cost were incurred in the retrieval smoke. The 600-word limit is explicitly not a model-token budget.

Local per-query retrieval timing is hardware-specific and excludes corpus acquisition and generation. The first 25 records are a deterministic smoke sample, not a representative quality benchmark. Unit-test fixtures are synthetic and used only to verify software behavior.

See `results/phase1` for compact reports and manifests. Raw data, full traces, upstream checkout, and remote output remain in ignored directories. Original source documents remain intact except the review's status line now records user approval and implementation start.

## Next baseline milestone

Resolve the original router adapter and API snapshot; map the target published experiment; choose exact generator/judge/checkpoints and supported Kaggle memory settings; record a compatible remote environment; then run a bounded real-answer pilot. Preserve differences as explicit adaptations if exact assets cannot be obtained. Do not proceed to research-effect claims before this gate.

Sources: [pinned upstream](https://github.com/USTCAGI/PruningRAG/tree/cfae4e46e73144b07df84d7760f759e39db54062), [dataset](https://huggingface.co/datasets/fishsure/RM3QA/tree/f56a19b1348559be73b7ae4e4626d0d2ed778b21), [router release issue](https://github.com/USTCAGI/PruningRAG/issues/1), and the checked-in audit/data artifacts.
