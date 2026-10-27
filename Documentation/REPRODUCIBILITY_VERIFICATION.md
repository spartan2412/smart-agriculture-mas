# Reproducibility Verification — Official v2.2 Release

This document records reproducibility for the final paper evidence release of
the **Multi-Agent Smart Agriculture Decision System – A RAG-Grounded
Multi-Agent Framework for Multimodal Decision Support in Precision
Agriculture**.

The official boundary is the 19 versioned archives in
[OFFICIAL_V2_2_RELEASE_MANIFEST.json](../results/v2_2-paper-artifacts/OFFICIAL_V2_2_RELEASE_MANIFEST.json).
It deliberately excludes the dated recoverable history at
[results/archive/2026-10-12-pre-v2_2](../results/archive/2026-10-12-pre-v2_2/).
Reproducibility here means repeatability of frozen source-grounded evidence,
decision traces, and stated policy behavior; it is not irrigation, fertilizer,
disease, yield, market-profit, or farmer-outcome accuracy.

## 1. Final v2.2 release verification

The final clean-commit verification is stored in
[results/v2_2-final-reproducibility-2026-10-12](../results/v2_2-final-reproducibility-2026-10-12/).

| Verification item | Denominator | Official v2.2 result | What was compared |
| --- | ---: | ---: | --- |
| Frozen artifact hashes | 57 | 57/57 exact | Registry, scenarios, enrichments, RAG/operation scope, prompts, Oracle/runtime artifacts, and related frozen inputs recorded by the release verifier. |
| E0 scenario outputs | 300 | 300/300 exact | Normalized structural fingerprints, all 20 Oracle check vectors, semantic traces, decisions, citations, and detailed farmer messages. |
| Conflict fixtures | 60 | 60/60 exact | Normalized deterministic policy traces. |
| Provenance/alignment fixtures | 60 | 60/60 exact | Normalized block/exposure policy traces. |
| E1 acceleration evidence | 1 bound artifact | refreshed | Ollama Metal residency for the same accepted 7B artifact, including 4,638,040,390 GPU-resident model bytes. |

The exact-match rate is `exact normalized matches / compared records`. For
example, the E0 trace rate is `300 / 300 = 100%`; it is a software/evidence
repeatability rate, not an agricultural accuracy value. The twenty Oracle
checks are individually evaluated binary contract properties; the aggregate
`overall_structural_pass` row is derived from all twenty and is not an
additional check.

## 2. Semantic equality rule

The verifier evaluates `evaluation/reproducibility_verification.py` outputs
after both the reference and a fresh reproduction are persisted. Exact
semantic equality covers:

- scenario identity and frozen source/enrichment/RAG/operation hashes;
- all 20 Oracle check values and structural fingerprint;
- typed claims, source citations, retrieved passages, plan items, decisions,
  conflict records, and farmer-facing message;
- for fixture suites, the labelled policy behavior and block boundary; and
- for model preflight, backend/model identity, generation settings, and Apple
  Metal evidence.

The comparison intentionally excludes elapsed time, peak RSS, timestamps,
run-directory names, and Git commit strings. They remain manifest telemetry,
but are not semantic decision evidence and may vary between equal runs.

## 3. Model-enabled boundary

The accepted E1-v5.1 model-enabled evidence was already generated under its
separate frozen held-out and pilot protocol:

- [results/e1-v5-heldout-final](../results/e1-v5-heldout-final/) is the
  one-time immutable 96-question relevance result;
- [results/v2_2-e1-v5-30site-pilot](../results/v2_2-e1-v5-30site-pilot/) is
  the accepted 30-site full-MAS pilot; and
- [results/v2_2-e1-v5-full-mas](../results/v2_2-e1-v5-full-mas/) is the
  accepted 300-scenario model-enabled archive.

The final v2.2 release verification refreshed the same artifact’s Metal
evidence but did **not** rerun the expensive 300-scenario model-enabled batch.
That restraint avoids creating a new unreviewed model-result generation after
the official E1 archive was frozen. Earlier clean-checkout E0/E1 semantic
reproduction is retained as historical material in the dated archive and may
be discussed only with that qualification.

## 4. Reproduction procedure for a future version

Do not overwrite official archives. From a clean committed checkout, use a
new, versioned output location and record the exact command, environment,
model artifact, and source hashes.

```zsh
# Deterministic E0, including conflict fixtures; use a new local output path.
.venv-macos/bin/python -m evaluation.benchmark_batch_runner \
  --configuration E0 \
  --output-dir results/local-e0-reproduction \
  --include-conflict-fixtures

# The independent provenance/alignment fixture suite.
.venv-macos/bin/python -m evaluation.provenance_fixture_runner \
  --output-dir results/local-provenance-reproduction

# Compare against the official v2.2 reference without modifying it.
.venv-macos/bin/python -m evaluation.reproducibility_verification \
  --configuration E0 \
  --reference-dir results/v2_2-e0-full-mas \
  --reproduction-dir results/local-e0-reproduction \
  --conflict-reference-dir results/v2_2-e0-full-mas \
  --conflict-reproduction-dir results/local-e0-reproduction \
  --provenance-reference-dir results/v2_2-provenance-gate-fixtures \
  --provenance-reproduction-dir results/local-provenance-reproduction \
  --output-dir results/local-reproducibility-report
```

For a new model-enabled reproduction, first create fresh bound-model Metal
evidence through the preflight procedure in
[APPLE_GPU_PREFLIGHT.md](APPLE_GPU_PREFLIGHT.md). Keep the final held-out set
immutable: any prompt, candidate-package, model, parser, or runtime change
requires a newly versioned development and held-out protocol before its result
can be compared with E1-v5.1.

## 5. Interpreting any mismatch

A changed hash, missing scenario, changed citation/condition, changed
selected ID, changed conflict handling, or changed farmer message is a
reproducibility failure. Retain and report it; do not silently regenerate the
reference or tune the system until it matches. A latency or memory difference
alone is descriptive telemetry, not a semantic mismatch.

All metric formulas, source files, exact numerators, and interpretation limits
are in [RESULTS.md](RESULTS.md#exact-metric-formulas-denominators-and-input-data).
