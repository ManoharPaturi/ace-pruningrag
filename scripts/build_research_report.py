"""Render a bounded research-status report from committed execution evidence."""

import argparse
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file, write_json

SOURCES = {
    "cohort": "results/version1/cohort/gpu_summary.json",
    "paired": "results/version1/cohort/paired_metrics.json",
    "reviews": "results/version1/cohort/ai_method_summary.json",
    "retained": "results/version1/retained_trace_audit.json",
    "nli": "results/version1/nli_verification.json",
    "nli_comparison": "results/version1/nli_review_comparison.json",
    "extraction": "results/version1/extraction_verification.json",
    "extraction_audit": "results/version1/extraction_audit.json",
    "live": "results/version1/live_demo_verification.json",
    "retry_control": "results/phase4/regeneration/control_comparison.json",
    "constrained": "results/version1/constrained_verification.json",
    "constrained_alignment": "results/version1/constrained_alignment_replay.json",
    "constrained_progress": "results/version1/constrained_review_progress.json",
    "constrained_comparison": "results/version1/constrained_control_comparison.json",
    "unicode_replay": "results/version1/unicode_policy_replay.json",
    "unicode_submission": "results/version1/unicode_submission.json",
}


def render(root):
    data = {key: read_json(root / name) for key, name in SOURCES.items()}
    gpu, paired, review = (data[k] for k in ("cohort", "paired", "reviews"))
    retained, nli, extraction, live = (data[k] for k in ("retained", "nli", "extraction", "live"))
    if gpu["queries"] != 50 or gpu["actual_llm_calls"] != 250:
        raise ValueError("report requires the executed 50-question five-selector cohort")
    if (
        gpu["maximum_reserved_tokens"] > 2048
        or review["validation"]["ai_reviewed_responses"] != 250
    ):
        raise ValueError("cohort budget or review coverage differs")
    if (
        review["independent_human_review"] is not False
        or retained["admitted_response_records"] != 444
    ):
        raise ValueError("report interpretation/review scope differs")
    if nli["trace_sha256"] != data["nli_comparison"]["nli_trace_sha256"]:
        raise ValueError("NLI comparison binding differs")
    if extraction["source_trace_sha256"] != review["validation"]["trace_sha256"]:
        raise ValueError("extraction source differs from reviewed cohort")
    if extraction["trace_sha256"] != data["extraction_audit"]["extraction_trace_sha256"]:
        raise ValueError("extraction audit binding differs")
    retry = data["retry_control"]
    if retry["initial_questions"] != 6 or any(
        retry[k] != 8
        for k in (
            "retry_answers",
            "same_retry_prompt_as_all_source_control",
            "same_retry_answer_as_all_source_control",
        )
    ):
        raise ValueError("historical control scope differs from report")
    expected_ai = {"correct": 41, "incorrect": 68, "uncertain": 53, "abstained": 88}
    if review["validation"]["ai_semantic_verdicts"] != expected_ai:
        raise ValueError("AI aggregate differs from frozen report scope")
    for name in ("mmr", "joint", "exact", "coverage"):
        item = paired["paired_differences"][name]["literal_agreement"]
        expected = (0.0, [-0.06, 0.06]) if name == "coverage" else (0.02, [0.0, 0.06])
        if (item["mean_difference"], item["bootstrap_95_percentile_interval"]) != expected:
            raise ValueError("bootstrap scope differs from frozen report")
    if len(data["nli_comparison"]["incorrect_answer_entailment_examples"]) != 27:
        raise ValueError("NLI disagreement count differs")
    constrained = data["constrained"]
    progress = data["constrained_progress"]
    source_review_state = (
        f"{progress['unreviewed_source_proposals']} valid source proposals still require "
        "role review. The partial source review covers"
        if progress["unreviewed_source_proposals"]
        else "All valid source proposals have qualitative AI role assessments. "
        "The completed source review covers"
    )
    comparison = data["constrained_comparison"]
    if (
        constrained["trace_sha256"] != progress["extraction_trace_sha256"]
        or comparison["control_trace_sha256"] != extraction["trace_sha256"]
        or comparison["constrained_trace_sha256"] != constrained["trace_sha256"]
        or not all(
            comparison[k] is True
            for k in (
                "all_task_bindings_equal",
                "all_prompts_equal",
                "all_input_token_counts_equal",
            )
        )
    ):
        raise ValueError("constrained control/report bindings differ")
    methods = ("top_k", "mmr", "coverage", "joint", "exact")
    table, ai_table = [], []
    for name in methods:
        m = gpu["per_method"][name]
        cost = paired["per_method"][name]
        judgments = review["per_method"][name]
        if m["answers"] != 50 or judgments["responses"] != 50 or judgments["pending"] != 0:
            raise ValueError("method response coverage differs")
        v = judgments["ai_verdicts"]
        if sum(v.values()) != 50:
            raise ValueError("AI verdict totals differ")
        table.append(
            f"| {name} | {m['literal_matches']} | {m['abstentions']} | "
            f"{cost['input_tokens']:,} | {cost['output_tokens']:,} |"
        )
        ai_table.append(
            f"| {name} | {v['correct']} | {v['incorrect']} | {v['uncertain']} | {v['abstained']} |"
        )
    phases = [
        (
            "1: reproduction",
            "Locked inputs, real GPU retrieval, adapted generation",
            "Original checkpoints, full API backing and paper experiment contract",
        ),
        (
            "2: complementary selection",
            "Five selectors, 250 outputs and full AI audit",
            "Independent requirements/support sets and cross-source/source-only controls",
        ),
        (
            "3: adaptive retrieval",
            "Deterministic routing and historical snapshot costs",
            "Legitimate learned-router labels/calibration and fresh evaluation",
        ),
        (
            "4: reliability",
            "Bounded retries, NLI/extraction and retained failures",
            "General semantic support, complete claims and measured regeneration benefit",
        ),
        (
            "5: research/product",
            "Asynchronous demo and evidence-bound report draft",
            "Full ablations, fresh entity/event audit, independent metrics and final paper",
        ),
    ]
    phase_table = "\n".join("| " + " | ".join(row) + " |" for row in phases)
    report = f"""# ACE-PruningRAG: executed development experiments and open research gates

Generated from committed evidence. This is a reproducible research-status draft, not
an independently validated paper result or a completed five-phase roadmap.

## Abstract

ACE-PruningRAG investigates complementary evidence selection under a fixed request
budget. The implemented adapted pipeline completed {gpu["queries"]} shared questions
across five selectors, producing {gpu["actual_llm_calls"]} answers. All admitted
{retained["admitted_response_records"]} answer records have source-bound AI assessments;
those records include repeated policies and retries, not independent questions.
The selector experiment is web-only and uses lexical proxies rather than reviewed
support labels. Literal agreement and AI judgments do not establish a winning method.
Independent source/answer NLI diagnostics and structured extraction expose verification
failures. A browser-to-GPU demonstration survives API restart and page refresh. Faithful
original reproduction, genuine cross-source necessity, complete support labels, fresh
independent evaluation, general claim verification and full ablations remain incomplete.

## Hypothesis and implemented boundary

The hypothesis is that a set of evidence can answer requirements that its individual
items cannot. Test this by comparing shared candidate pools, generator and full model
budgets, and by running each source alone as a control. Different source names or low
text similarity do not establish complementarity.

The implemented selector supports relevance, coverage, redundancy and pair additions,
plus bounded exact search. In the executed cohort, coverage means query-term proxies;
groups/conflicts are disabled. Exact search optimizes that proxy objective, not a
reviewed support oracle. All 12 candidates come from pinned web snapshots, with at
most five excerpts selected. The generator is Qwen2.5-1.5B-Instruct revision
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, float32 CUDA, greedy decoding, seed 42.
Each complete rendered request, including chat/provenance wrappers and the 96-token
output reserve, is capped at 2,048 tokens. The observed maximum is
{gpu["maximum_reserved_tokens"]:,}. This is an adapted generator/configuration; it
is not the original published PruningRAG baseline.

The originally frozen 50-question packet excluded recorded pilot IDs, duplicate
question text and overlapping canonical source pages. Inspecting and reviewing these
outputs converted this cohort into development data. Entity/event disjointness and
independent sealed-test status are not established. Do not tune on these questions
and continue to call them unseen evaluation.

## Selector outcomes

All values below are across 50 shared questions per method. Top-K selects by relevance;
MMR balances relevance and redundancy; coverage prioritizes the lexical requirement
proxy; joint uses the combined implemented objective; exact enumerates the bounded
candidate set. Their consumed token counts differ despite the same upper budget.

| Method | Literal matches | Exact abstentions | Input tokens | Output tokens |
| --- | ---: | ---: | ---: | ---: |
{chr(10).join(table)}

Literal matching is the frozen reference-string diagnostic, not semantic accuracy.
Exact abstention recognizes the frozen short form; AI review separately records four
prose abstentions. Question-level bootstrap comparisons use 10,000 resamples, seed 42.
MMR/joint/exact each differ from top-K by +0.02 literal agreement with exploratory
95% percentile interval [0, 0.06]; coverage differs by zero, interval [-0.06, 0.06].
No multiple-comparison adjustment or entity/event independence is established.
These results do not demonstrate grounded semantic improvement.

| Method | AI-correct | AI-incorrect | AI-uncertain | AI-abstained |
| --- | ---: | ---: | ---: | ---: |
{chr(10).join(ai_table)}

These are complete source-bound AI development judgments, not independent human
accuracy labels. Total judgments are 41 correct, 68 incorrect, 53 uncertain and 88
abstained. Some factually plausible answers lack selected support; some follow a
source while missing the question's period, relation, answer type or completeness.
All original outputs and human exports remain separate. Coverage's lower context
cost and greater abstention cannot be promoted as better quality from these data.

The cohort used {gpu["input_tokens"]:,} input / {gpu["output_tokens"]:,} output tokens,
{gpu["shared_candidate_retrievals"]} shared candidate retrievals and
{gpu["actual_llm_calls"]} generation calls. Model loading took
{gpu["model_loading_seconds"]:.2f} seconds; generation took
{gpu["generation_seconds"]:.2f} seconds. These exclude queue, acquisition, setup and
local reconstruction, and are not a production latency guarantee. Monetary cost is
not established; compute/tokens and call counts are the recorded costs. Assistant
AI-review token costs are outside the experiment's engine ledger and are not measured.
Zero pipeline judge calls does not mean those reviews had no model cost. These
per-run figures are not a reconciled whole-project bill; retained copies/superseded
outputs cannot be summed as new calls without provider execution identity.

## Reliability diagnostics and retained negative results

The historical closing-price path validates a narrow entity/date/field contract.
Eight actual retries reproduce their direct all-source control's context, prompt
and answer, adding generation cost without an observed answer change on six shared
questions. This is a development control, not representative routing performance.
Missing currency/adjustment metadata remains unresolved; no ticker-based assumption
fills those fields. General web claim verification is not established by this path.

The independent NLI diagnostic scored {nli["scored_pairs"]:,} source/answer pairs and
skipped {nli["unscored_pairs"]} pairs over the full token cap, without truncation. It
used {nli["classifier_forward_calls"]} classifier forward passes and zero answer
calls. At least one raw entailment occurs for 27 AI-incorrect answers: an all-time
count can follow a source but miss a decade question. The classifier and AI audit
have different targets; this is not classifier precision, recall or accuracy.
Raw text entailment must not automatically accept a QA response.

The unconstrained extractor completed {extraction["extraction_sequences"]} sequences
in {extraction["generate_invocations"]} batched invocations, using
{extraction["input_tokens"]:,} unpadded / {extraction["padded_input_tokens"]:,} padded
input tokens and {extraction["output_tokens"]:,} output tokens. None of 50 question
proposals passes the required schema/span contract. Only six of 336 source proposals
passes it; AI review finds role/scope problems in five of those six. The remaining
historical water-level tuple does not establish a current answer or external truth.
All 1,105 question/source comparisons remain unresolved. Schema/span validation
exposes failures; it does not prove semantic roles. The separate constrained experiment
completed the same 386 tasks and passed complete reconstruction. Its completed
proposals include {constrained["validation_counts"]["constrained_span_proposal"]} structurally
valid objects and one retained capped invalid object, compared with six valid objects
in the control. Task identities, prompts, input counts and generator configuration
match; token filtering and its dependency overlay are changed factors. It used
{constrained["output_tokens"]:,} output tokens, with the same 124,383 unpadded inputs.
Generation took {constrained["timing"]["generation_seconds"]:.2f} seconds and model loading
{constrained["timing"]["model_loading_seconds"]:.2f} seconds; constraint preparation and
other setup are excluded, so these do not establish an end-to-end speed improvement.

None of 1,105 constrained literal comparisons has complete unambiguous alignment:
950 are unresolved and 155 have different explicit fields. All 50 question proposals
have AI role rationales; 48 are partial/misbound, one is a coherent minimal count core,
and one has underspecified query scope. These post-hoc categories are qualitative,
not calibrated accuracy. {source_review_state}
{progress["AI_reviewed_source_proposals"]} records / {progress["distinct_reviewed_source_pairs"]}
distinct text/proposal pairs. Its coherent-claim judgments cover
{progress["source_review_counts"]["coherent_claim_in_excerpt"]} records but only
{progress["distinct_coherent_source_pairs"]} distinct pairs; repeated copies are not
independent confirmation. Mixed facts, missing subjects, metadata and field-role
errors remain visible. These qualitative AI categories do not establish calibrated
accuracy or external truth. Structural success is not general support or complete
claim coverage; automatic acceptance remains disabled. See
[constrained reconstruction and review](CONSTRAINED_EXTRACTION.md).

The [versioned Unicode correction](UNICODE_SPAN_POLICY.md) preserves combining marks
in lexical words without normalizing source text. Full replay of 386 unchanged old
outputs rejects one truncated-name proposal that v1 permitted. This is a policy
revalidation, not corrected neural generation or semantic-role improvement. The
submitted v1 source, all outputs and all previous outcome counts remain intact.

A separate corrected-policy GPU worker was submitted as private kernel
`{data["unicode_submission"]["kernel_id"]}`, version
{data["unicode_submission"]["submitted_version"]}. Its submission record reports
{data["unicode_submission"]["provider_status_last_observed"]} at the recorded observation,
with a cap of 386 extraction sequences / 97 generate invocations. Completed execution,
decoded outputs and measured costs remain unverified; submission and local protocol
tests do not establish corrected neural results or semantic improvement.

Query-only form checks retain source-identifier answers and incomplete/unparsed lists
as warnings. The strict rectangle calculator requires explicit geometry and compatible
units; it is not silently applied to arbitrary room questions. Across all 444 admitted
outputs, 12 form warnings occur and narrow explicit scope/date checks add no additional
findings. Missing information remains unresolved rather than becoming a correction.

The retained inventory contains {retained["trace_paths"]} stored trace paths,
{retained["stored_response_records"]} stored records and
{retained["response_records_in_unique_trace_files"]} records across
{retained["unique_trace_files"]} distinct trace-file hashes. Only 444 are admitted.
Failed float16 punctuation outputs, superseded generations and duplicate downloads
remain separate from outcome counts. Every declared retained local answer trace has
AI audit coverage; this does not prove completeness of all possible remote artifacts.

## Product demonstration

The separate browser request returned `{live["prediction"]}` using one actual model
call, {live["input_tokens"]:,} input / {live["output_tokens"]} output tokens and
{live["maximum_reserved_tokens"]:,} reserved tokens. API restart during RUNNING and
browser refresh recovered the same journal job without resubmission. Observed request
creation to verified completion was {live["request_creation_to_verified_completion_seconds"]:.2f}
seconds, including queue/setup/transfer/reconstruction and restart recovery; these
components are not individually separated. This one inspected case verifies the
bounded fixed-web asynchronous path, not broad QA quality, adaptive multi-source
execution or general claim support. Raw answers, evidence provenance, replay/live
states and warnings remain visible.

## Completion requirements still open

| Phase | Executed evidence | Missing completion evidence |
| --- | --- | --- |
{phase_table}

Independent human review cannot be manufactured by this assistant. Source-bound AI
review and robust engineering do not satisfy that gate.
The [completion audit](VERSION1_COMPLETION_AUDIT.md)
and [next-version plan](VERSION2_PLAN.md) retain the full objective and promotion gates.
Do not label these experiments publication-ready or report an unverified selector win.

## Reproduce this report

From the repository root, write to fresh output paths:

```sh
uv run --locked --no-editable python scripts/build_research_report.py \\
  --output runs/report-reconstruction/RESEARCH_REPORT.md \\
  --manifest runs/report-reconstruction/manifest.json
```

The manifest hashes every committed input artifact, the report and its renderer. It
establishes report provenance, not independent scientific truth. The underlying GPU
reconstruction/audit commands and limitations are documented in
[selector results](COHORT_SELECTOR_RESULTS.md), [retained audit](RETAINED_RESPONSE_AUDIT.md),
[NLI diagnostics](NLI_SUPPORT_DIAGNOSTIC.md),
[extraction diagnostics](STRUCTURED_CLAIM_EXTRACTION.md)
and [live-flow evidence](LIVE_DEMO_FLOW.md). Full private traces and review records are
required to independently reconstruct those runs; public summaries alone are weaker
than that reconstruction. Owner-only main merging remains unchanged.
"""
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists() or a.manifest.exists():
        raise FileExistsError("report output paths must be new")
    root = Path.cwd()
    report = render(root)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(report)
    write_json(
        a.manifest,
        {
            "scope": "Executed development report provenance, not independent truth",
            "sources_sha256": {name: sha256_file(root / name) for name in SOURCES.values()},
            "renderer_sha256": sha256_file(root / "scripts/build_research_report.py"),
            "report_sha256": sha256_file(a.output),
            "publication_ready": False,
            "five_phase_goal_complete": False,
        },
    )


if __name__ == "__main__":
    main()
