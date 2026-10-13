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
    "unicode_execution": "results/version1/unicode_verification.json",
    "unicode_comparison": "results/version1/unicode_control_comparison.json",
    "unicode_reviews": "results/version1/unicode_review_progress.json",
    "inventory_preflight": "results/version1/inventory_preflight.json",
    "inventory_submission": "results/version1/inventory_submission.json",
    "movie_assets": "results/phase1/movie_asset_verification.json",
    "movie_index": "results/phase1/movie_index.json",
    "movie_http": "results/phase1/movie_snapshot_smoke.json",
    "movie_names": "results/phase1/movie_name_index.json",
    "movie_name_http": "results/phase1/movie_name_smoke.json",
    "movie_name_sequences": "results/phase1/movie_name_score_sequences.json",
    "inventory_execution": "results/version1/inventory_verification.json",
    "inventory_audit": "results/version1/inventory_structural_audit.json",
    "inventory_valid_reviews": "results/version1/inventory_valid_review_progress.json",
    "requirements_preflight": "results/version1/requirements_preflight.json",
    "requirements_submission": "results/version1/requirements_submission.json",
    "requirements_execution": "results/version1/requirements_verification.json",
    "requirements_reviews": "results/version1/requirements_review_progress.json",
    "movie_evidence": "results/phase1/movie_evidence_smoke.json",
    "requirements_3b_preflight": "results/version1/requirements_3b_preflight.json",
    "requirements_3b_match": "results/version1/requirements_3b_preflight_comparison.json",
    "requirements_3b_submission": "results/version1/requirements_3b_submission.json",
    "requirements_3b_execution": "results/version1/requirements_3b_verification.json",
    "requirements_3b_reviews": "results/version1/requirements_3b_review_progress.json",
    "requirements_models": "results/version1/requirements_model_comparison.json",
    "inventory_roles": "results/version1/inventory_role_review_progress.json",
    "requirements_contract": "results/version1/requirements_contract_diagnostic.json",
}


def render(root):
    data = {key: read_json(root / name) for key, name in SOURCES.items()}
    requirements_run, requirements_reviews, movie_evidence = (
        data[k] for k in ("requirements_execution", "requirements_reviews", "movie_evidence")
    )
    model_preflight, model_match, model_submission = (
        data[k]
        for k in (
            "requirements_3b_preflight",
            "requirements_3b_match",
            "requirements_3b_submission",
        )
    )
    model_run, model_reviews, model_comparison, inventory_roles, contract = (
        data[k]
        for k in (
            "requirements_3b_execution",
            "requirements_3b_reviews",
            "requirements_models",
            "inventory_roles",
            "requirements_contract",
        )
    )
    if (
        model_run["trace_sha256"] != model_reviews["extraction_trace_sha256"]
        or model_reviews["execution_verification_sha256"]
        != sha256_file(root / SOURCES["requirements_3b_execution"])
        or model_comparison["variant_trace_sha256"] != model_run["trace_sha256"]
        or model_comparison["control_trace_sha256"] != requirements_run["trace_sha256"]
        or model_comparison["variant_review_progress_sha256"]
        != sha256_file(root / SOURCES["requirements_3b_reviews"])
        or model_reviews["AI_reviewed_proposals"] != 50
        or model_reviews["structurally_bound_proposals"] != 5
        or model_comparison["variant_bound_with_all_clause_roles_null"] != [0, 8, 11, 18, 25]
        or model_comparison["semantic_requirement_improvement_established"] is not False
        or inventory_roles["valid_review_progress_sha256"]
        != sha256_file(root / SOURCES["inventory_valid_reviews"])
        or inventory_roles["AI_assessed_tasks"] != 111
        or inventory_roles["rejected_inventories_pending_assessment"] != 275
        or inventory_roles["all_inventory_tasks_assessed"] is not False
        or contract["policy_sha256"] != model_run["span_policy_sha256"]
        or contract["prompt_says_nullable_operation_fields"] is not True
        or contract["actual_model_calls"] != 0
    ):
        raise ValueError("completed model/rejected-review/contract bindings differ")
    if (
        model_preflight["tasks"] != 50
        or model_match["same_encoded_input_ids"] is not True
        or model_match["control_preflight_sha256"]
        != sha256_file(root / SOURCES["requirements_preflight"])
        or model_match["variant_preflight_sha256"]
        != sha256_file(root / SOURCES["requirements_3b_preflight"])
        or model_submission["preflight_sha256"]
        != sha256_file(root / SOURCES["requirements_3b_preflight"])
        or model_submission["preflight_comparison_sha256"]
        != sha256_file(root / SOURCES["requirements_3b_match"])
        or model_submission["tasks_sha256"] != requirements_run["tasks_sha256"]
        or model_submission["completed_execution_verified"] is not False
        or model_submission["semantic_requirement_improvement_established"] is not False
    ):
        raise ValueError("pending model-variant task/preflight/submission scope differs")
    if (
        requirements_run["status"] != "requirements_spans_decode_and_costs_reconstructed"
        or requirements_run["tasks"] != 50
        or requirements_run["trace_sha256"] != requirements_reviews["extraction_trace_sha256"]
        or requirements_reviews["execution_verification_sha256"]
        != sha256_file(root / SOURCES["requirements_execution"])
        or requirements_reviews["AI_reviewed_proposals"] != 50
        or requirements_reviews["structurally_bound_proposals"] != 0
        or requirements_reviews["independent_human_review"] is not False
        or requirements_reviews["answer_acceptance_enabled"] is not False
        or data["requirements_submission"]["preflight_sha256"]
        != sha256_file(root / SOURCES["requirements_preflight"])
        or movie_evidence["probe_config_sha256"]
        != sha256_file(root / "configs/movie_evidence_probe.json")
        or movie_evidence["generator_config_sha256"]
        != sha256_file(root / "configs/generated_pilot.json")
        or movie_evidence["queries"] != 3
        or movie_evidence["actual_answer_generation_calls"] != 0
        or movie_evidence["cross_source_benefit_established"] is not False
    ):
        raise ValueError("query-requirement or movie candidate proof/review scope differs")
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
    movie_index, movie_http = data["movie_index"], data["movie_http"]
    if (
        data["movie_assets"]["status"] != "assets_verified"
        or movie_http["status"] != "movie_id_year_snapshot_HTTP_verified"
        or movie_http["index_manifest_sha256"] != sha256_file(root / SOURCES["movie_index"])
        or movie_http["index_sha256"] != movie_index["index_sha256"]
        or movie_http["record_counts"] != movie_index["record_counts"]
        or movie_http["cross_source_benefit_established"] is not False
    ):
        raise ValueError("movie asset/index/HTTP bindings differ")
    inventory = data["inventory_preflight"]
    inventory_run, inventory_audit, inventory_reviews = (
        data[k] for k in ("inventory_execution", "inventory_audit", "inventory_valid_reviews")
    )
    if (
        inventory_run["status"] != "inventory_spans_decode_and_costs_reconstructed"
        or inventory_run["trace_sha256"] != inventory_audit["extraction_trace_sha256"]
        or inventory_run["trace_sha256"] != inventory_reviews["extraction_trace_sha256"]
        or inventory_reviews["structural_audit_sha256"]
        != sha256_file(root / SOURCES["inventory_audit"])
        or inventory_reviews["execution_verification_sha256"]
        != sha256_file(root / SOURCES["inventory_execution"])
        or inventory_reviews["AI_reviewed_valid_inventories"] != 21
        or inventory_reviews["full_semantic_review_complete"] is not False
        or inventory_reviews["answer_acceptance_enabled"] is not False
    ):
        raise ValueError("inventory completed-execution/review bindings differ")
    name_sequences = data["movie_name_sequences"]
    if (
        name_sequences["name_manifest_sha256"] != sha256_file(root / SOURCES["movie_names"])
        or name_sequences["source_index_sha256"] != movie_index["index_sha256"]
        or not all(p["ranked_score_sequence_matches_reference"] for p in name_sequences["probes"])
        or name_sequences["semantic_identity_verified"] is not False
    ):
        raise ValueError("movie-name score/record bindings differ")
    if (
        inventory["tasks"] != 386
        or inventory["all_tasks_fit"] is not True
        or inventory["actual_model_calls"] != 0
        or inventory["source_trace_sha256"] != progress["source_trace_sha256"]
        or inventory["prompt_policy_sha256"]
        != sha256_file(root / "src/ace_pruningrag/claim_inventory.py")
        or data["inventory_submission"]["preflight_sha256"]
        != sha256_file(root / SOURCES["inventory_preflight"])
    ):
        raise ValueError("inventory prompt/preflight/submission bindings differ")
    unicode_run, unicode_compare, unicode_reviews = (
        data[k] for k in ("unicode_execution", "unicode_comparison", "unicode_reviews")
    )
    if (
        unicode_run["status"] != "unicode_spans_decode_and_costs_reconstructed"
        or unicode_run["trace_sha256"] != unicode_compare["revised_trace_sha256"]
        or unicode_run["trace_sha256"] != unicode_reviews["extraction_trace_sha256"]
        or unicode_reviews["execution_verification_sha256"]
        != sha256_file(root / SOURCES["unicode_execution"])
        or unicode_reviews["control_comparison_sha256"]
        != sha256_file(root / SOURCES["unicode_comparison"])
        or unicode_reviews["original_review_progress_sha256"]
        != sha256_file(root / SOURCES["constrained_progress"])
        or unicode_reviews["records_bound"] != 386
        or unicode_reviews["unreviewed_tasks"] != 0
        or unicode_reviews["independent_human_review"] is not False
        or unicode_reviews["answer_acceptance_enabled"] is not False
    ):
        raise ValueError("Unicode execution/control/review bindings differ")
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

A separate corrected-policy GPU worker completed as private kernel
`{data["unicode_submission"]["kernel_id"]}`, version
{data["unicode_submission"]["submitted_version"]}. The initial submission record's RUNNING
status is historical. Full reconstruction verifies {unicode_run["extraction_sequences"]}
extraction sequences / {unicode_run["generate_invocations"]} generate invocations, 124,383
unpadded input tokens, {unicode_run["output_tokens"]:,} output tokens and 890 maximum
reserved tokens. Generation took {unicode_run["timing"]["generation_seconds"]:.2f} seconds;
constraint preparation and other setup are excluded from this timing.

Task identities, messages and input token counts match the v1 control; runtime snapshots
also match. There are {unicode_compare["output_comparison"]["changed_raw_proposals"]} changed
raw proposals and {unicode_compare["output_comparison"]["unchanged_raw_proposals"]} unchanged
ones. The changed output preserves the combining-mark name, but its award category,
song and period still mix different rows. Its fresh AI assessment remains mixed facts.
All 386 tasks have bound assessments: 385 exact-input/proposal reviews reused and one
fresh changed-proposal review. Structural outcomes remain 385 valid and one capped
invalid JSON. This executes and verifies the lexical correction; it does not establish
semantic role improvement, independent accuracy or automatic acceptance.

The plural [claim-inventory decoder](CLAIM_INVENTORY.md) now has a closed JSON/list
grammar, private worker and independent reconstruction path. Pinned-tokenizer preflight
fits all 386 real tasks, totaling {inventory["input_tokens"]:,} input tokens with
{inventory["maximum_reserved_request_tokens"]:,} maximum reserved request tokens.
The changed prompt and expanded 2,048-output / 4,096-request caps are separate
experimental factors, not a matched-budget comparison to the six-field decoder.
Private kernel `{data["inventory_submission"]["kernel_id"]}`, version 1, completed;
its initial QUEUED observation is historical. Reconstruction verifies 386 sequences /
97 generate invocations, 174,027 input tokens (198,260 padded),
{inventory_run["output_tokens"]:,} output tokens and 2,907 maximum reserved tokens.
The generation interval was {inventory_run["timing"]["generation_seconds"]:.2f} seconds,
including token filtering during generation and excluding constraint preparation.
Structural outcomes are 21 valid inventories, 361 rejected inventories and four
retained capped JSON failures. Twenty valid queries remain partial/misbound under
qualitative AI review; the one valid source is an unrelated conditional geometry
example with role errors. All 21 valid inventories are review-bound, while 365
rejected inventories lacked assessment at the initial valid-only checkpoint.
Parsed frames total 66 query
and 1,551 source frames; only 21 frames are structurally admitted. Neither grammar
nor a proposed_complete status establishes exhaustive requirements or role quality.

The [extended inventory assessment](CLAIM_INVENTORY.md) now covers 111 tasks:
all fifty query inventories and 61 source inventories, including ninety rejected
outputs. The 111 task records contain 107 distinct input/proposal pairs and 353
parsed frames; 275 rejected source tasks remain unassessed. Source observations
include navigation-as-facts, caption dates borrowed for unrelated events, missing
row/actor associations and procedural examples promoted into assertions. Coherent
partial facts are retained without establishing full coverage or external truth.

The separately versioned [query-only logical representation](QUERY_REQUIREMENTS.md)
preserves known conditions independently of unknown answer/intermediate variables.
The diagnostic completed all 50 extraction sequences in 13 generate invocations:
{requirements_run["input_tokens"]:,} input tokens,
{requirements_run["padded_input_tokens"]:,} padded input tokens,
{requirements_run["output_tokens"]:,} output tokens and
{requirements_run["maximum_reserved_request_tokens"]:,} maximum reserved tokens.
The generation interval was {requirements_run["timing"]["generation_seconds"]:.2f}
seconds; model loading took {requirements_run["timing"]["model_loading_seconds"]:.2f}
seconds. All 50 outputs are complete JSON but fail requirement validation. All fifty
have exact-output-bound qualitative AI role/omission reviews, with mixed roles,
misplaced cardinality, missing measurements and self-dependent operations. This is
a retained negative result, not independently measured accuracy. The extraction
gate fails; no source-support or answer-acceptance promotion follows.

A separately pinned [3B extractor model variant](REQUIREMENTS_MODEL_VARIANT.md)
has now been submitted with the same fifty tasks, prompts, grammar, FP32, seed,
batch size and explicit control decoding defaults. Preflight verifies identical
input token IDs for all fifty requests. The 3B checkpoint's default repetition
penalty differs; it is explicitly restored to the control value of 1.1. Private
kernel `{model_submission["kernel_id"]}`, version 1, completed; its initial RUNNING
observation is historical. All fifty sequences / thirteen invocations reconstruct,
with matching actual runtime/dependency identities and input tokens. The variant
produced {model_run["output_tokens"]:,} output tokens in a
{model_run["timing"]["generation_seconds"]:.2f}-second generation interval, with
{model_run["timing"]["model_loading_seconds"]:.2f} seconds of model loading.
Five proposals pass structural validation and 45 fail; all five admitted proposals
have only null clause roles. Every output has bound AI role/omission review, and
all fifty remain misbound/incomplete under that qualitative assessment. Structural
counts do not establish semantic improvement; timing is not an unbiased hardware
benchmark. The answer generator and acceptance boundary remain unchanged.

A retained post-hoc synthetic [contract diagnosis](REQUIREMENTS_MODEL_VARIANT.md)
identifies prompt/grammar/validator misalignment: nullable operation fields are
allowed by decoding but rejected for known operations; a fixed variable role
rejects an entity used as subject in one edge and object in another unless its role
is erased to unknown; nonempty clause text with no linked roles can pass structural
validation. These engineering demonstrations make zero model calls and do not
alter either frozen run's scores. Correct the contract in a separate protocol before
attributing all failures to model capacity or escalating model size again.

The original [movie/person/year snapshot](MOVIE_SNAPSHOT.md) is now restored separately:
three checksum-verified files totaling {data["movie_assets"]["bytes"]:,} bytes. A disk-backed
index covers {movie_index["record_counts"]["movie"]:,} movie,
{movie_index["record_counts"]["person"]:,} person and {movie_index["record_counts"]["year"]}
year records. It retains {movie_index["repeated_id_records"]["person"]} repeated person-ID
records with the original last-record-wins lookup behavior. Actual movie/person ID,
year and missing-ID loopback responses match original snapshot records. The original
endpoint's 1990–2021 year gate is retained although
the stored snapshot includes years through 2024. This validates three structured
lookup paths. Generated source-only comparisons and cross-source benefit remain
unverified. No generator or judge runs as part of this restoration.

A separate disk-backed BM25 name index now implements movie/person name requests.
Returned scores and ranked score sequences match the pinned reference in seven real
probes, and HTTP records match source rows. Ranked IDs differ in five probes because
the explicit source-row tie policy differs from NumPy ordering at equal scores.
This restores name retrieval with a disclosed ordering adaptation; exact original
ranking, semantic entity identity and cross-source benefit remain unverified.

[Movie field candidates](MOVIE_EVIDENCE.md) now join the web pool through a separate
adapter. Exact field-value/record provenance and pinned-tokenizer budgets pass on
three inspected development queries: five actual local name lookups and eighteen
prepared web-only/API-only/combined requests across top-K and joint selectors.
The same twelve-item union-ranked pool is filtered for all three source controls.
Two queries admit no API fields into that pool; the API-only contexts remain empty
and the combined contexts remain web-only. The director query admits two API fields.
This exposes lexical retrieval exclusion rather than proving API irrelevance.
These are source-fidelity and request-preparation checks with zero answer generations.
Manual query-copied lookup proposals are not a trained router; entity identity,
snapshot-time applicability, semantic support and cross-source benefit remain open.

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
