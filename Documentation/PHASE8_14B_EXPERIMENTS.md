# Phase 8: 14B Capacity and Deployment Experiments

## Purpose and boundary

Phase 8 evaluates optional 14B bounded-LLM deployments against the already
frozen v5.1 evidence-selection contract. It does not change agricultural
sources, scenarios, enrichments, RAG scope, agents, candidate packaging,
prompts, oracle rules, or action permissions.

The 96 source-derived v5.1 questions were originally held out for E1. For E2
and E3 they are a **frozen transfer evaluation**: neither 14B configuration
was tuned using them. They are not a newly claimed independent held-out set.

The test measures bounded fact-ID selection quality only. It does not measure
farm outcomes, irrigation accuracy, fertilizer-dose accuracy, disease accuracy,
yield, profit, or farmer preference.

## Configurations and artifact boundary

| Configuration | Backend | Bound artifact | Apple-GPU preflight | Comparison status |
| --- | --- | --- | --- | --- |
| E1-v5 | Ollama / Metal | Qwen2.5 7B Instruct Q4_K_M | Verified, 4,638,040,390 GPU-resident bytes | Accepted reference model-enabled configuration. |
| E2 | Ollama / Metal | Qwen2.5 14B, GGUF Q4_K_M | Verified, 9,092,695,325 GPU-resident bytes | 14B capacity experiment. |
| E3 | MLX-LM / Apple GPU | `mlx-community/Qwen2.5-14B-Instruct-4bit`, MLX 4-bit | Verified, 8,441,014,600 observed Metal bytes | Deployment-backend experiment only. |

E2 and E3 share the Qwen2.5 14B Instruct family and fixed v5.1 generation
settings (temperature 0.0, 200 maximum tokens, three maximum selected facts).
They do **not** use byte-identical artifacts: E2 is a locally installed GGUF
artifact and E3 is an MLX 4-bit safetensors artifact. In addition, Ollama does
not expose an upstream source commit or standalone tokenizer hash in local
metadata. Therefore, E2-versus-E3 differences must never be attributed solely
to runtime.

The exact binding, artifact hashes, model identities, and source URLs are
stored in [`e2-e3-artifact-binding.json`](../results/e2-e3-artifact-binding.json).

## Preflight result

Each preflight made a harmless JSON-generation request and required observed
model residency in the active runtime before any evaluation could start.

| Configuration | Evidence artifact | Result |
| --- | --- | --- |
| E2 | [`acceleration_evidence.json`](../results/v2_2-e2-apple-gpu-preflight/acceleration_evidence.json) | Verified Ollama Metal residency for the exact 14B GGUF blob. |
| E3 | [`acceleration_evidence.json`](../results/v2_2-e3-apple-gpu-preflight/acceleration_evidence.json) | Verified MLX generation and non-zero Metal allocation for the exact local artifact tree. |

GPU preflight proves runtime configuration only. It does not establish that a
model satisfies the selection-quality acceptance criteria.

## Frozen relevance-transfer results

All runs used the same 96 questions, v5.1 role instructions, candidate
packaging, conditions, thresholds, and source-backed candidate IDs. The
acceptance policy requires precision/recall and safe-empty accuracy of at least
80%, exact RAG precision/recall of at least 75%, and invalid-output/fallback
rates at most 2%.

| Measure | E1-v5 7B accepted reference | E2 Ollama 14B | E3 MLX 14B |
| --- | ---: | ---: | ---: |
| Accepted selections | 96/96 | 87/96 | 72/96 |
| Fact precision / recall | 98.6% / 98.6% | 97.3% / 100.0% | 98.6% / 100.0% |
| Safe-empty accuracy | 100.0% | 96.7% | 96.7% |
| Exact RAG passage precision / recall | 100.0% / 100.0% | 100.0% / 100.0% | 100.0% / 100.0% |
| Invalid structured-output rate | 0.0% | 9.375% | 25.0% |
| Fallback rate | 0.0% | 0.0% | 0.0% |
| Mean per-question latency | 2,470 ms | 5,858 ms | 6,931 ms |
| Acceptance gate | Pass | **Fail** | **Fail** |

The E2 and E3 failures are solely the pre-registered invalid structured-output
rate. The strict bounded selector rejected outputs whose `selected_fact_ids`
field was not a list of strings; it did not treat them as successful empty
selections. The result deliberately stores the validator outcome and error
class, not untrusted model prose. This behavior is a safety feature: a
malformed model response cannot influence an agricultural claim or action.

E2 recorded nine invalid structured outputs, concentrated in safe-empty
market, satellite, and farmer-explanation requests. E3 recorded 24, including
the safe-empty weather requests. There were no transport/runtime fallbacks.

## Consequence for pilots and full MAS runs

Neither E2 nor E3 advanced to the 30-site full-MAS pilot or a 300-scenario
model-enabled run. The protocol explicitly requires relevance acceptance before
that scaling step. Starting a pilot after this failure would misrepresent the
pre-registered experiment sequence.

E1-v5 remains the only accepted model-enabled 300-scenario configuration. The
deterministic E0 and controlled A0--A6 results are unchanged.

## Appropriate interpretation and future work

This is a useful negative result:

- larger parameter count did not satisfy the strict structured-output
  reliability gate under this exact frozen selection interface;
- Apple-GPU availability is necessary for local deployment but not sufficient
  for a model to be admitted to the MAS pilot;
- the fail-closed bounded selector prevents malformed output from weakening
  provenance, safety, or farmer-action restrictions.

Do not alter the v5.1 prompt, candidate packaging, parser, question labels, or
thresholds and rerun these same records. A future 14B system would require a
new versioned selection implementation, a separate development set, a new
held-out protocol, and a fresh pilot gate. It must still report E2/E3 as a
deployment-backend comparison rather than a pure runtime-only comparison unless
byte-equivalent artifacts can be proven.

## Reproducibility artifacts

| Artifact | Contents |
| --- | --- |
| [`E2 run manifest`](../results/v2_2-e2-v5-relevance-14b/run_manifest.json) | E2 runtime, binding, exact question hashes, commit, and completion metadata. |
| [`E2 metrics`](../results/v2_2-e2-v5-relevance-14b/aggregate_relevance_metrics.json) | Aggregate, role-level selection, latency, and schema metrics. |
| [`E2 acceptance`](../results/v2_2-e2-v5-relevance-14b/acceptance_report.json) | Pre-registered check-by-check failed/passed decision. |
| [`E3 run manifest`](../results/v2_2-e3-v5-relevance-14b-mlx/run_manifest.json) | E3 MLX runtime, binding, exact question hashes, commit, and completion metadata. |
| [`E3 metrics`](../results/v2_2-e3-v5-relevance-14b-mlx/aggregate_relevance_metrics.json) | Aggregate, role-level selection, latency, memory, and schema metrics. |
| [`E3 acceptance`](../results/v2_2-e3-v5-relevance-14b-mlx/acceptance_report.json) | Pre-registered check-by-check failed/passed decision. |
