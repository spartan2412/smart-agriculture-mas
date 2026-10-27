# Final v2.2 Reproducibility Verification — 12 October 2026

## Purpose

This archive is the final clean-checkout reproducibility verification for the
official v2.2 research evidence. It reruns only the deterministic reference
path and controlled fixtures; it does not generate data, modify prompts,
tune a model, or overwrite an accepted result archive.

The rerun began from clean commit `a55c17e3a550a9ef2ae261ae581e05712bb7540c`.

## Checks completed

| Verification | Result |
| --- | --- |
| Fresh deterministic E0 run | 300/300 scenarios completed and structurally passed |
| Structural oracle fingerprints | 300/300 exact matches to `v2_2-e0-full-mas` |
| Individual oracle-check vectors | 300/300 exact matches |
| Full semantic traces | 300/300 exact matches |
| Farmer decisions/messages, citations, retrieved passages, and conflicts | 300/300 exact matches |
| Frozen artifacts | 57/57 SHA-256 checks pass |
| Conflict-policy fixtures | 60/60 pass; normalized policy trace exactly matches |
| Provenance/alignment fixtures | 60/60 pass; policy trace exactly matches |
| Direct farm actions in provenance fixtures | 0 |

The 57 hash checks span the scenario and registry artifacts, all four
enrichment/RAG layers (19 files), benchmark-agent and workflow code,
bounded-LLM/prompt runtime code, oracle/protocol code, held-out evaluation
records, fixture registries, and pilot/relevance inputs. The complete,
file-level evidence is in
[`e0-verification/e0_reproducibility_result.json`](e0-verification/e0_reproducibility_result.json).

## Fresh Apple Metal evidence

The E1 local-runtime preflight was also repeated on the clean commit. It
verified the bound `qwen2.5:7b-instruct` Q4_K_M Ollama artifact:

| Field | Observed value |
| --- | --- |
| Host | Apple M5, arm64, 24 GiB unified memory |
| Runtime | Ollama 0.34.2 |
| GPU mechanism | Ollama Metal / Apple GPU, verified from `/api/ps` residency |
| GPU-resident model bytes | 4,638,040,390 |
| Artifact SHA-256 | `2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730` |
| Ollama digest | `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e` |
| Temperature / maximum selected facts | 0.0 / 3 |

PyTorch MPS is intentionally not treated as proof of Ollama acceleration.
The preflight instead invokes Ollama and confirms nonzero GPU residency for
the exact bound model. See
[`e1-apple-gpu-preflight/acceleration_evidence.json`](e1-apple-gpu-preflight/acceleration_evidence.json).

## Scope and interpretation

- This establishes reproducibility of the deterministic v2.2 E0 result and
  both deterministic fixture-policy suites.
- The environment manifest records Python, dependency freeze, macOS, Git, and
  Ollama facts for this execution. See
  [`e0-verification/environment_manifest.json`](e0-verification/environment_manifest.json).
- The accepted E1-v5 full MAS result already has a separate clean-checkout
  semantic reproduction record. This final pass refreshes its exact
  model/Metal evidence without rerunning the 300-scenario model-enabled batch.
- E2/E3 are intentionally excluded: both are frozen negative transfer results
  that failed the structured-output acceptance gate before pilot/full-MAS
  execution.
- These checks establish source-contract, trace, oracle, and policy
  reproducibility. They do not establish field-level agricultural outcome
  accuracy.

## Archive layout

| Directory | Contents |
| --- | --- |
| `e0-full-mas-reproduction/` | Fresh 300-scenario deterministic run and 60 conflict-fixture traces |
| `provenance-gate-fixtures-reproduction/` | Fresh 60 malformed provenance/alignment fixture results |
| `e0-verification/` | Independent comparison, all hash checks, fixture comparisons, and environment manifest |
| `e1-apple-gpu-preflight/` | Fresh exact E1 Ollama/Metal/model artifact verification |
