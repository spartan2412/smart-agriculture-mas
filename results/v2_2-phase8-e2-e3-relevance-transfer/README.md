# Phase 8: 14B Deployment Transfer Evaluation (v2.2)

## Purpose

This archive records a **frozen transfer evaluation** of the existing v5.1
bounded-evidence selector on two Apple-GPU 14B deployments.  It does not tune
prompts, candidate packaging, source evidence, or model behavior.  The same
immutable 96-question E1-v5.1 held-out set and pre-registered acceptance
criteria were used for E2 and E3.

The experiment distinguishes two questions:

1. Can a higher-capacity 14B deployment emit the bounded structured-selection
   schema reliably enough for the MAS?
2. If both qualifying deployments used an identical 14B artifact, could their
   runtime behavior be compared?

The answer to the second question is limited here: E2 and E3 share the Qwen2.5
14B base family and parameter count, but their artifact format and
quantization differ.  They are therefore a **deployment-backend comparison**,
not a pure runtime-only comparison.

## Frozen protocol and acceptance rule

The acceptance policy is `v5.1-heldout-acceptance-1`:

| Measure | Requirement |
| --- | ---: |
| Fact-selection precision / recall | at least 80% each |
| Safe-empty accuracy | at least 80% |
| Exact RAG passage precision / recall | at least 75% each |
| Invalid structured-output rate | at most 2% |
| Fallback rate | at most 2% |

A configuration that fails this relevance gate must be reported but cannot
advance to a 30-site full-MAS pilot or the 300-scenario execution.  This stops
an unreliable model response before it can enter a full decision pipeline.

## Result

| Configuration | Deployment | Apple-GPU evidence | Valid selections | Invalid outputs | Fallbacks | Mean latency | Acceptance |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| E1-v5.1 reference | Ollama, Qwen2.5 7B | previously verified | 96 / 96 | 0.0% | 0.0% | 2,470 ms | Pass |
| E2 | Ollama, Qwen2.5 14B Q4_K_M GGUF | Metal residency: 9.09 GB | 87 / 96 | 9.4% | 0.0% | 6,431 ms | **Fail** |
| E3 | MLX-LM, Qwen2.5 14B 4-bit MLX | Metal residency: 8.44 GB | 72 / 96 | 25.0% | 0.0% | 7,876 ms | **Fail** |

Both E2 and E3 met the source-selection quality thresholds among their parsed
outputs: each had 100% fact recall, 100% exact RAG passage precision and
recall, and 96.7% safe-empty accuracy.  They failed only the structured-output
validity threshold.  E2's invalid rate was 9/96 and E3's was 24/96, both above
the 2% maximum.

## Consequences

- Neither E2 nor E3 was allowed to run its 30-site MAS pilot.
- Consequently, neither was allowed to run the 300-scenario MAS batch.
- No full-MAS oracle, safety, farmer-message, or memory comparison is claimed
  for E2/E3, because those runs were correctly blocked.
- The primary model-enabled result remains E1-v5.1 (Ollama Qwen2.5 7B).
- The negative results strengthen the paper's safety claim: model capacity and
  Apple-GPU residency alone do not grant deployment permission; structured
  output must satisfy the frozen gate.

## Artifact boundary

The exact artifact relationship is recorded in
[`../e2-e3-artifact-binding.json`](../e2-e3-artifact-binding.json).

| Configuration | Artifact / quantization | Revision visibility |
| --- | --- | --- |
| E2 | Ollama `qwen2.5:14b`, GGUF `Q4_K_M` | Ollama does not expose a base-model revision locally |
| E3 | `mlx-community/Qwen2.5-14B-Instruct-4bit`, MLX 4-bit safetensors | `dad510143ae5cdb1466778bde3161460f9e9f604` |

The artifacts are not identical.  E2 versus E3 must never be interpreted as
the isolated effect of Ollama versus MLX-LM.

## Reproducible records

- [E2 Metal preflight](../v2_2-e2-apple-gpu-preflight/acceleration_evidence.json)
- [E2 acceptance report](../v2_2-e2-v5-relevance-14b/acceptance_report.json)
- [E2 aggregate metrics](../v2_2-e2-v5-relevance-14b/aggregate_relevance_metrics.json)
- [E3 MLX preflight](../v2_2-e3-apple-gpu-preflight/acceleration_evidence.json)
- [E3 acceptance report](../v2_2-e3-v5-relevance-14b-mlx/acceptance_report.json)
- [E3 aggregate metrics](../v2_2-e3-v5-relevance-14b-mlx/aggregate_relevance_metrics.json)
- [E1 final held-out reference](../e1-v5-heldout-final/final_acceptance_report.json)

Each relevance archive includes all 96 per-question selections, expected IDs,
latencies, parsed validity events, and immutable run metadata.
