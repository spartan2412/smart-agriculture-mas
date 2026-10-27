# Apple-GPU Pilot Preflight

> **Final v2.2 update:** a fresh clean-commit E1 preflight again verified the
> bound Qwen2.5 7B Q4_K_M Ollama Metal artifact, recording 4,638,040,390
> GPU-resident bytes. See
> [`results/v2_2-final-reproducibility-2026-10-12`](../results/v2_2-final-reproducibility-2026-10-12/).

## Purpose

This preflight proves that a local bounded-LLM experiment is configured with
the intended frozen model and was observed using Apple GPU memory before a
30-scenario MAS pilot begins. It is a runtime/reproducibility check, not an
agricultural benchmark result and not a substitute for the subsequent pilot.

## Frozen pilot population

[`data/pilot_sets/apple_gpu_30_anchor_scenarios`](../data/pilot_sets/apple_gpu_30_anchor_scenarios/)
contains exactly the original 30 verified anchor scenarios:

- one scenario for each final study site;
- five sites for each of rice, wheat, maize, chickpea, soybean, and tomato;
- no supplementary scenarios, synthetic cases, or newly collected evidence.

The set is hash-locked to its source anchor manifest. The batch runner can use
only this population for the documented 30-scenario local-model pilot.

## E1 verified hardware preflight

The frozen E1 evidence is
[`acceleration_evidence.json`](../results/v2_2-e1-v5-apple-gpu-preflight/acceleration_evidence.json).

| Item | Recorded result |
| --- | --- |
| Host | Apple Silicon Mac (`Apple M5`, `arm64`) |
| Unified memory | 24 GiB |
| Runtime | Ollama 0.34.2 |
| Model | `qwen2.5:7b-instruct`, Qwen2.5 7B Instruct |
| Quantization | `Q4_K_M` |
| Bound model blob SHA-256 | `2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730` |
| Ollama digest prefix | `845dbda0ea48` |
| Observed GPU-resident bytes | 4,638,040,390 |
| Probe result | Valid local JSON response; configured model remained listed by Ollama after the probe |

The evidence is marked `verified` only because a local Ollama JSON request
completed for the exact E1 tag; `/api/ps` immediately listed that same model
with `size_vram > 0`; the model digest prefix, on-disk blob SHA-256, and
`Q4_K_M` quantization matched the frozen protocol; and the host was macOS on
`arm64` with non-zero unified memory.

For Ollama, `torch.backends.mps.is_available()` is deliberately **not** used
as acceleration proof. Ollama runs through its own Metal runtime. The accepted
E1 proof is the runtime's own GPU-residency observation after an actual local
inference request.

## Boundary and completed use

The hardware evidence was a prerequisite, not a result by itself. The frozen
v5.1 held-out set was subsequently run once under this exact E1 artifact and
passed every pre-registered selection-quality threshold. The accepted runtime
then passed the 30-site pilot (30/30 structural-oracle passes) and the full
300-scenario E1-v5/A0 run (300/300 passes, 2,400 accepted bounded selections,
zero fallback/invalid/direct-action events). The complete Phase 7 comparison
is in [`results/v2_2-phase7-controlled-comparison`](../results/v2_2-phase7-controlled-comparison/).

This remains evidence about local runtime configuration and bounded evidence
selection, not farm-outcome accuracy. E2 and E3 now have separately bound,
verified 14B Apple-GPU preflights, but neither passed the following frozen
selection-quality gate: E2 recorded 9.375% and E3 25.0% invalid structured
outputs, exceeding the pre-registered 2% maximum. Neither advanced to a
30-site MAS pilot. The artifacts are backend-native (GGUF versus MLX), so
their comparison is not runtime-only. See
[`PHASE8_14B_EXPERIMENTS.md`](PHASE8_14B_EXPERIMENTS.md).

The preflight refuses to overwrite an existing result. After held-out
acceptance, the formal pilot was run from a clean committed checkout with the
frozen evidence file passed to `evaluation.benchmark_batch_runner`. The runner
accepts the 30-site pilot only through its exact hash-locked CSV. The command
below is the recorded E1 command shape used by the now-validated v5.1 runtime;
the accepted pilot and full 300-scenario result are already preserved in the
project result archives:

```bash
.venv-macos/bin/python -m evaluation.benchmark_batch_runner \
  --configuration E1 \
  --pilot-scenario-set data/pilot_sets/apple_gpu_30_anchor_scenarios/scenario_ids.csv \
  --acceleration-evidence-json results/v2_2-e1-v5-apple-gpu-preflight/acceleration_evidence.json \
  --output-dir results/local-e1-30-site-pilot
```

The current bounded-LLM environment variables must be enabled for that formal
run. Any arbitrary partial subset, altered pilot CSV, or conflicting
`--scenario-id` argument is rejected.
