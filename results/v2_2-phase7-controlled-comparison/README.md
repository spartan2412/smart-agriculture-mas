# Phase 7 Controlled Comparison

This package reads only persisted result artifacts. It does not rerun a model, call Ollama, modify a trace, or create a new agricultural label.

## What it establishes

- E0 and E1-v5 used the identical ordered 300-scenario population, shared frozen data hashes, and the same external-oracle schema.
- E1-v5 retained the full structural safety boundary while recording its bounded-LLM status, latency, and memory behavior.
- The final 96-question held-out relevance benchmark is the sole source of selection-quality metrics. The 300-scenario run does not relabel that population or create a second relevance-accuracy claim.
- A0–A6 and both fixture suites are regenerated in `architecture-ablation/` from their persisted inputs.
- Six paired farmer messages are included only as qualitative inspection material; they are not a subjective score or agricultural outcome assessment.

## What it does not establish

It does not establish irrigation accuracy, fertilizer-dose accuracy, disease diagnosis accuracy, yield impact, profitability, or farmer preference.

## Reproduce

```bash
.venv-macos/bin/python -m evaluation.final_phase7_comparison \
  --output-dir results/phase7-controlled-comparison
```

The command fails closed if the E0/E1 scenario population, shared frozen data hashes, trace identities, oracle metric schema, E1 bounded-role coverage, or final held-out acceptance result is inconsistent.
