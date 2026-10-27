# Bounded-LLM v5.1 Final Held-Out Evaluation Protocol

## Status

This protocol freezes the final model-quality evaluation boundary after v5.1
development. The observed E1-v4 benchmark and both v5.1 development
iterations are not final model-quality evidence. No v5 prompt or candidate
packaging change may be based on the held-out result.

## Held-out population

The final set contains 96 source-derived questions: 12 for each of the eight
bounded roles. It uses 12 date-specific frozen scenarios from six verified
crop--district--season sites that are disjoint from both previous relevance
sets at **both scenario and site level**.

| Crop | Unseen site | Contexts |
| --- | --- | ---: |
| Rice | Bathinda, Punjab | 2 |
| Wheat | Bathinda, Punjab | 2 |
| Maize | Ariyalur, Tamil Nadu | 2 |
| Chickpea | Nanded, Maharashtra | 2 |
| Soybean | Baran, Rajasthan | 2 |
| Tomato | Coimbatore, Tamil Nadu | 2 |

Each candidate fact, source identity, condition, RAG passage, plan card, and
expected selection is derived from the scenario's immutable, source-gated
runtime bundle. No farm outcome, live field observation, new source, or
synthetic agronomic operation is introduced.

The RAG questions are deliberately unambiguous: each names the exact
source-scoped operation and its recorded required condition. This corrects the
ambiguity found during development without exposing an evaluator-only passage
position as the answer.

## Pre-registered relevance thresholds

The machine-readable thresholds are frozen in
[`acceptance_criteria.json`](../data/llm_relevance_heldout/acceptance_criteria.json)
and hash-bound by the held-out manifest.

| Metric | Requirement |
| --- | ---: |
| Fact-selection precision | ≥ 80% |
| Fact-selection recall | ≥ 80% |
| Safe-empty selection accuracy | ≥ 80% |
| Exact RAG passage precision | ≥ 75% |
| Exact RAG passage recall | ≥ 75% |
| Invalid structured-output rate | ≤ 2% |
| Fallback rate | ≤ 2% |

Passing these thresholds establishes bounded evidence-selection quality only.
It does not establish agricultural outcome accuracy.

## Required sequence

1. Build once into `data/llm_relevance_heldout/`; the builder refuses overwrite.
2. Verify question, acceptance-policy, frozen-source, and frozen-v5-runtime hashes.
3. The final held-out runner is implemented and mock-tested with zero model
   calls. Run Qwen2.5 7B / Ollama Metal exactly once under that runner.
4. Do not tune v5.1 based on this output.
5. If relevance thresholds pass, run the separate E1-v5 30-site full-MAS pilot.
6. The pilot must retain 30/30 external-oracle passes and zero structural regressions.
7. Only then scale E1-v5 to all 300 scenarios.

## Artifacts

- Builder: [`evaluation/bounded_llm_relevance_heldout.py`](../evaluation/bounded_llm_relevance_heldout.py)
- Build command: [`scripts/build_bounded_llm_relevance_heldout_set.py`](../scripts/build_bounded_llm_relevance_heldout_set.py)
- Frozen questions: `data/llm_relevance_heldout/heldout_questions.jsonl`
- Manifest: `data/llm_relevance_heldout/manifest.json`
- Frozen pre-model experiment manifest:
  `results/e1-v5-heldout-preflight/experiment_manifest.json`
- Final runner: [`evaluation/bounded_llm_relevance_v5_heldout.py`](../evaluation/bounded_llm_relevance_v5_heldout.py)

## Final frozen outcome

The one permitted v5.1 held-out run is complete and is retained without any
post-result prompt or candidate-packaging change. Its result is in
[`results/e1-v5-heldout-final`](../results/e1-v5-heldout-final/):

| Metric | Result |
| --- | ---: |
| Fact-selection precision / recall | 98.6% / 98.6% |
| Safe-empty accuracy | 100.0% |
| Exact RAG passage precision / recall | 100.0% / 100.0% |
| Invalid structured-output / fallback rate | 0.0% / 0.0% |

The acceptance report passed all pre-registered thresholds. The separate
30-site pilot and full 300-scenario E1-v5/A0 runtime then completed without a
structural regression. These results remain bounded evidence-selection and
runtime results—not agricultural outcome, field-action, or farmer-preference
accuracy.
