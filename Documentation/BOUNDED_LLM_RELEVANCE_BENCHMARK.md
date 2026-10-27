# Bounded-LLM Relevance Benchmark

## Purpose

The optional LLM layer in the Multi-Agent Smart Agriculture Decision System is
not allowed to generate agricultural facts or recommendations. It may only
rank source-approved fact IDs already admitted by the deterministic MAS.

The existing 20-check Oracle verifies that a completed MAS trace obeys its
frozen evidence-and-safety contract. It cannot determine whether one local LLM
model chooses more relevant allowed facts than another, because safety gates
prevent every model from changing the final action boundary. This separate
benchmark measures that bounded selection quality before E1, E2, and E3
model/runtime experiments begin.

It is not farm-outcome ground truth and does not evaluate irrigation, fertilizer
dose, crop protection, yield, market profit, or disease accuracy.

## Status relative to v5.1

This is the observed **E1-v4** relevance benchmark and local-model baseline.
It remains immutable and reportable as historical evidence, but it is not the
final quality estimate for the improved v5.1 selector. V5.1 development was
performed only on its separate development set and stopped after iteration 02.
The final v5.1 measurement is the disjoint, hash-checked set in
[`data/llm_relevance_heldout`](../data/llm_relevance_heldout/), with its own
pre-registered acceptance criteria and no-tuning rule. See
[`BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md`](BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md).

## Frozen composition

| Item | Value |
| --- | ---: |
| Question records | 96 |
| Bounded roles | 8 |
| Questions per role | 12 |
| Frozen scenarios | 12 anchor scenarios |
| Focused crops | 6 |
| Candidate-selection limit | 3 fact IDs |
| Prompt template | `bounded-selection-v4-structured-relevance-prompts` |
| Direct farm actions permitted | 0 |

The selected population contains two location-specific anchor scenarios for
each focused crop: rice, wheat, maize, chickpea, soybean, and tomato. It spans
the project’s Punjab, Tamil Nadu, Maharashtra, and Madhya Pradesh crop-site
contexts while remaining a fixed evaluation subset rather than a new dataset.

## Roles and labels

| Bounded role | Positive relevance target | Empty-selection boundary |
| --- | --- | --- |
| Weather Context | Exact-window historical weather/water context | Never current field moisture, an irrigation order, or forecast evidence. |
| Soil Context | Static SoilGrids representative-cell context | Never a field soil test, plant-available N/P/K value, or dose basis. |
| Satellite/NDVI Context | Quality-valid representative-cell scene/trend context | Never disease, crop stage, parcel condition, or irrigation evidence. |
| Market Evidence | Source-published historical crop-district comparison | Never a live quotation, price forecast, or sell/hold recommendation. |
| Fertilizer Baseline | Regional nutrient-plan reference and/or field-dose restriction | Never personalized NPK calculation or application order. |
| Official Operations RAG | Matching source-scoped operation or exact-crop post-harvest passage | Never an out-of-scope source or relaxed condition. |
| Provenance-Aware Coordinator | Matching approved regional plan card | Never decision status, gate, feasibility, or conflict-policy override. |
| Farmer Explanation/Citation | Requested optional historical context card | Never an optional card used to create a farm-specific action. |

Each role receives 12 questions. The set contains both positive relevance
cases and controlled empty-selection cases. An empty expected selection is
correct only when the supplied question seeks an inference that the role’s
source scope cannot support.

## Source-derived record schema

Every JSONL question contains:

| Field | Meaning |
| --- | --- |
| `question_id`, `agent_name`, `scenario_id` | Stable evaluation identity. |
| `scenario_context`, `farmer_question` | Frozen crop, location, season, date, geometry, and relevance request. |
| `allowed_source_document_ids` | Source identities represented by the candidate set. |
| `allowed_fact_ids`, `allowed_passage_ids`, `allowed_facts` | The only identifiers and source-backed text the LLM may select. |
| `expected_admissible_fact_ids`, `expected_admissible_passage_ids` | Source-derived relevant selections. |
| `expected_plan_or_operation_ids` | Applicable plan/operation identifiers when a question tests such a selection. |
| `required_conditions` | Scope, field-condition, temporal, or safety condition that selection must preserve. |
| `disallowed_distractor_ids` | Other source-backed facts from the same scenario that are admissible evidence but irrelevant to this role/question. |
| Prompt hashes/version | Locks the exact role objective and shared selection contract. |

Candidate facts come only from the same scenario’s typed claims, regional plan
items, retrieved official passages, exact-crop post-harvest passages, or
deterministic decision trace. The benchmark never creates invented values,
operations, citations, conditions, or fabricated distractors.

## Integrity checks

The builder and loader fail closed unless all of the following hold:

1. Exactly 96 questions exist, with exactly 12 for each approved role.
2. Every expected fact or passage belongs to that question’s allowed set.
3. Every non-expected allowed ID is recorded as a distractor.
4. Every candidate retains a non-empty source-document identity.
5. Every question retains a required condition/scope boundary.
6. The question-file SHA-256 matches `manifest.json`.
7. Every input source artifact and every eight-role prompt source hash matches
   the manifest.

This lets a future E1–E3 run fail instead of silently evaluating a changed
prompt, source bundle, plan, operation record, or scenario context.

## Future metrics

For each question, the runner records selected IDs, expected IDs, status,
prompt hash, latency, and peak process memory. It then reports:

| Metric | Definition |
| --- | --- |
| Fact precision / recall | Intersection of selected and expected fact IDs divided by selected / expected ID counts. |
| Top-k recall | Recall within the bounded three-ID selection limit. |
| Passage precision / recall | Same calculation restricted to official passage questions. |
| Plan/operation selection accuracy | Exact match between plan/operation IDs projected from selected facts and the source-derived expected IDs. |
| Empty-selection accuracy | Correctly returning no IDs on a question whose requested inference is out of scope. |
| Invalid structured-output rate | Proportion rejected by the immutable-ID or response-schema validator. |
| Fallback rate | Proportion safely degraded after an optional backend error. |
| Latency / memory | Mean, median, p95 latency and maximum process peak memory. |

Precision and recall are selection-quality metrics only. The model remains
unable to alter action status, citations, conditions, safety gates, or
conflict resolution even if it ranks a fact poorly.

## Artifacts and commands

The frozen data is in
[`data/llm_relevance_benchmark`](../data/llm_relevance_benchmark/). Rebuild
only when intentionally creating a new benchmark version:

```bash
.venv-macos/bin/python scripts/build_bounded_llm_relevance_benchmark.py
```

After the Apple-GPU pilot is independently verified, run a selected backend on
the fixed 96 questions:

```bash
.venv-macos/bin/python -m evaluation.bounded_llm_relevance \
  --output-dir results/local-e1-relevance-pilot
```

The observed E1-v4 result is retained as a historical baseline only. Final
model-quality evidence is the separately frozen v5.1 held-out evaluation,
which completed once with 98.6% fact precision/recall, 100% safe-empty and
exact RAG passage precision/recall, and zero invalid/fallback events. See
[`BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md`](BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md).
The present artifact remains immutable and must not be combined with the
held-out result as though it were a second final test.
