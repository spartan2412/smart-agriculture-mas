# E1 Bounded-LLM Relevance Error Analysis

## Purpose and scope

This document audits the first real local-model relevance evaluation. It is a diagnostic of the bounded selector's ranking quality, not an agricultural effectiveness result and not a structural-safety result.

- Configuration: **E1** — Ollama `qwen2.5:7b-instruct`, Q4_K_M, bounded-selection prompt v4.
- Historical run artifact: `results/archive/2026-10-12-pre-v2_2/development-history/e1-relevance-7b/`.
- Questions: 96 source-derived, frozen questions across eight bounded-LLM roles (12 per role).
- Execution commit: `1e7b71973cccc3ea5152327fa1a0cf9b7bca3a69`.
- Benchmark and prompt version: `1.0` / `bounded-selection-v4-structured-relevance-prompts`.
- Boundary: the selector can rank only already-admitted fact IDs, passage IDs, and plan/operation IDs. It cannot create an agricultural claim, citation, condition, operation, or direct farm action.

The benchmark artifacts and prompt-v4 result are frozen. This analysis does
**not** alter them. Its required follow-up has now been completed: v5.1 used a
separate development workflow through iteration 02, and a new scenario/site
disjoint held-out set was frozen. The final v5.1 held-out run subsequently
completed once and passed its pre-registered thresholds; that set may not be
used for further tuning. Its final evidence-selection result is reported in
[`RESULTS.md`](RESULTS.md#bounded-llm-apple-gpu-and-transfer-results) and the
immutable protocol remains
[`BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md`](BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md).

## Overall result

| Measurement | Result |
| --- | ---: |
| Accepted selections | 95 / 96 |
| Fact-selection precision | 68.9% |
| Fact-selection recall | 87.5% |
| RAG passage precision | 39.1% |
| RAG passage recall | 75.0% |
| Plan/operation-selection accuracy | 58.3% |
| Safe-empty selection accuracy | 10.0% (1 / 10) |
| Invalid structured outputs | 1 / 96 (1.0%) |
| Fallbacks | 0 / 96 |
| Mean selection latency | 2.53 s |

The low safe-empty score and low RAG passage precision mean E1-v4 must be reported as an initial local-model baseline, not as the final bounded-selection design.

## Error distribution by role

`Exact` means the complete selected ID set matched the source-derived expected set. `FP` and `FN` count extra and missed identifiers, respectively. An empty-set question asks the model to return no fact when the requested decision is unsupported.

| Role | Questions | Exact | Empty questions | Correct empty | FP | FN | Invalid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Weather context | 12 | 11 | 2 | 1 | 1 | 0 | 0 |
| Soil context | 12 | 10 | 2 | 0 | 2 | 0 | 0 |
| Satellite context | 12 | 10 | 2 | 0 | 2 | 0 | 0 |
| Market evidence | 12 | 10 | 2 | 0 | 2 | 0 | 0 |
| Fertilizer baseline | 12 | 2 | 0 | n/a | 24 | 8 | 0 |
| Official-operations RAG | 12 | 1 | 0 | n/a | 16 | 6 | 0 |
| Provenance-aware coordinator | 12 | 10 | 0 | n/a | 3 | 2 | 1 |
| Farmer explanation/citation | 12 | 10 | 2 | 0 | 2 | 0 | 0 |

The high exact scores for the simple context roles demonstrate that the local model can select an obvious, correctly scoped context item. The errors are concentrated in selection *discipline*: deciding when no evidence may be selected, choosing one exact operation passage rather than several near matches, and retaining the required fertilizer boundary.

## 1. Safe-empty selection errors

Ten questions deliberately requested an action that the supplied evidence cannot support. The model correctly selected nothing only once: the tomato irrigation-now weather question. It selected a relevant contextual fact in the remaining nine cases, even though that fact did not authorize the requested action.

| Role | Unsupported request | Model's incorrect selection | Failure pattern |
| --- | --- | --- | --- |
| Weather | Issue irrigation now | Historical weather context | Confuses historical context with an irrigation authorization. |
| Soil | Calculate field-specific NPK dose | Static SoilGrids context | Confuses a gridded predictor with a field soil test. |
| Satellite | Diagnose field disease | Representative-cell NDVI context | Confuses a contextual vegetation signal with diagnosis evidence. |
| Market | Make a sell/hold forecast | Historical mandi context | Confuses historical comparison with a forecast. |
| Explanation | Issue farm-specific action | Optional weather/satellite context | Confuses a usable explanatory card with sufficient action evidence. |

### Diagnosis

The current prompt asks whether a fact is relevant, while the negative questions ask whether it is *sufficient for the requested decision*. The model correctly recognizes topical relevance but insufficiently applies the stronger authorization test.

### Prompt-v5 requirement

For every role, add a first decision:

> Is any candidate both relevant **and sufficient for the exact requested decision under its allowed-use field**? If not, return an empty array. A contextual fact must not be selected merely because it concerns the same crop, location, or topic.

Each candidate should expose `allowed_use` and `does_not_establish` as distinct, compact fields. Safe-empty examples must use the exact decision domains of irrigation, field NPK dose, disease diagnosis, sell/hold forecast, and farm-specific action.

## 2. Official RAG passage-selection errors

The official-operations RAG role had 39.1% passage precision and 75.0% passage recall. Only 1 of 12 questions produced the exact expected set. This does **not** mean the system issued wrong advice: retrieved content is still filtered and downstream operations require deterministic scope, condition, and action-binding gates. It means the bounded LLM's ranking choice was often broader or less precise than the question required.

| Error family | Questions | Observed behavior | Example |
| --- | ---: | --- | --- |
| Extra near-match passages | 8 | Correct target was selected, but one extra crop-related passage was also selected. | Maize early-stage FAW treatment was paired with a pheromone-trap card. |
| Missed exact target | 3 | The intended source-scoped operation was omitted in favour of broader or different technical passages. | Soybean basal-fertilizer timing was replaced by irrigation and seed-treatment passages. |
| Exact selection | 1 | One source-scoped wheat harvest passage was selected alone. | `REL_RAG_03`. |

The three target misses were:

- `REL_RAG_02`: selected generic rice-harvest and contingency-disease passages instead of the archived, source-scoped rice maturity passage with its required condition.
- `REL_RAG_09` and `REL_RAG_10`: selected soybean irrigation and seed-treatment passages instead of the source-scoped basal-fertilizer timing passage.

### Diagnosis

The candidate list contains both `source_scoped_operation` and general `official_rag` layers. The prompt permits up to three selections and emphasizes relevance, so the model over-selects semantically related items. It does not consistently prioritize the exact source-scoped layer or the operation's recorded condition.

### Prompt-v5 and candidate-design requirements

1. Present `source_scoped_operation` candidates before generic RAG passages, with an explicit `operation_id`, `required_conditions`, and `scope_match` flag.
2. Ask for **one primary operation** when the user asks for an exact operation; permit a secondary passage only if it independently satisfies the same requested action and condition.
3. State that a general passage cannot replace a source-scoped operation when the latter is present and matched.
4. Add deterministic candidate grouping so duplicate fact/passages for the same operation are represented once to the LLM.
5. Include source-scope and condition-mismatch examples in the development set, especially soybean nutrient timing and rice maturity.

## 3. Fertilizer-plan ranking errors

The fertilizer role had only 2 exact selections out of 12. Its dominant failure was omission of the required `fertilizer:field_dose_boundary` while selecting irrelevant calendar or crop-protection cards.

| Observation | Count |
| --- | ---: |
| Questions that omitted the field-dose boundary | 8 / 12 |
| Questions with extra calendar/protection selections | 8 / 12 |
| Questions that selected the expected policy card and field-dose boundary exactly | 2 / 12 |
| Questions that retained the boundary but unnecessarily added regional-policy context | 2 / 12 |

For example, `REL_FERTILIZER_01` asks for both the regional nutrient-plan scope and the field-dose limit. The model retained the regional policy and fertilizer plan but substituted a crop-protection card for the field-dose boundary. This is a ranking error, not a safety failure: the deterministic fertilizer agent still independently emits the no-personalized-dose restriction.

### Diagnosis

The generic selection limit of three encourages broad topical cards. The field-dose boundary has an `abstain` disposition, whereas calendar and protection cards sound agriculturally useful. Prompt-v4 does not make a required safety boundary lexicographically higher priority than a broadly relevant plan card.

### Prompt-v5 and candidate-design requirements

1. Use a fertilizer-specific ranking order: **mandatory safety boundary → crop/region policy card → optional contextual card**.
2. Mark `required_for_answer=true` on a field-dose boundary when the question asks about a dose limit or why a dose is not issued.
3. Restrict the fertilizer role to two selection slots for a boundary question; omit calendar and protection cards from its candidate set unless the question explicitly requests them.
4. Explicitly state: a regional fertilizer policy cannot become a field dose, and the boundary must be selected whenever the answer refers to field-specific dosage.

## 4. Coordinator error

The coordinator was otherwise strong (10 exact selections out of 12). Its two errors were:

- `REL_COORDINATOR_07`: an invalid ID was produced for the expected chickpea calendar card. The schema validator rejected it, resulting in an empty safe selection.
- `REL_COORDINATOR_10`: the required soybean calendar card was selected, but the model also selected the conditional-operation decision and nutrient-policy card.

The invalid-ID guard worked as intended; invalid model output did not enter the downstream decision. Prompt-v5 should require the coordinator to choose one primary plan card when the question asks which card comes first and should show only canonical IDs.

## What changes now and what remains frozen

| Item | Status |
| --- | --- |
| Frozen scenarios, registry, enrichments, RAG corpus, source register | No change |
| E1-v4 benchmark, prompts, model results, and pilot results | Preserved as the initial baseline |
| Deterministic agent permissions, action gates, coordinator policy, and oracle | No change |
| V5.1 selector prompt and candidate packaging | Frozen after development iteration 02 |
| Final evaluation design | A separate held-out set is frozen; build/test its runner, evaluate it once, and do not tune against it |

## Next implementation sequence

1. Preserve this diagnostic and the observed E1-v4 result as the historical
   local-model baseline. **Completed.**
2. Build a scenario/site-disjoint development set, implement v5 role-specific
   packaging, and stop tuning after iteration 02. **Completed.**
3. Freeze the new source-derived held-out set and pre-register its thresholds.
   **Completed.**
4. Build and test its hash-checked runner with mocked responses. **Completed:**
   correct/safe-empty/invalid/fallback/irrelevant and tampering cases are
   covered without a real model call.
5. Evaluate the final held-out set once, then preserve the result without
   tuning. **Completed:** all pre-registered thresholds passed.
6. If accepted, run the fixed 30-site E1-v5 Apple-GPU pilot again.
   **Completed:** 30/30 external-oracle passes.
7. Scale only the accepted selector version to the 300 frozen scenarios.
   **Completed:** E1-v5/A0 passed 300/300 structural oracle checks with 2,400
   accepted bounded selections and zero fallback/invalid/direct-action events.

## Evidence locations

- Aggregate metrics: `results/archive/2026-10-12-pre-v2_2/development-history/e1-relevance-7b/aggregate_relevance_metrics.json`.
- Per-question selections and latency: `results/archive/2026-10-12-pre-v2_2/development-history/e1-relevance-7b/per_question/`.
- Historical E1 pilot safety/runtime verification: `results/archive/2026-10-12-pre-v2_2/historical-benchmark-runs/e1-30-site-pilot/`.
- Benchmark design: `Documentation/BOUNDED_LLM_RELEVANCE_BENCHMARK.md`.
- Final v5.1 protocol: `Documentation/BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md`.
- Historical development comparison: `results/archive/2026-10-12-pre-v2_2/development-history/`.
  The official final comparison is `results/v2_2-phase7-controlled-comparison/`.
