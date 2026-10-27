# Frozen Architecture Comparison

This directory is generated only from the persisted E0 and A1–A6 result artifacts plus the two stored fixture suites. It contains no new scenario, source, agricultural label, or model output.

## Interpretation boundary

- The 300 normal scenarios are an exhaustive fixed benchmark population, so tables report exact count/rate differences rather than farm-outcome accuracy or inferential significance tests.
- A1–A6 are declared evaluation-only systems. Their expected oracle failures identify the contract properties contributed by removed components.
- The conflict and provenance/alignment fixtures are controlled policy tests. They do not establish agricultural correctness or farmer impact.
- A5's normal 300-scenario equality with A0 is expected because the frozen records are valid. Its controlled fixture result, not the normal rate, demonstrates why the alignment validator remains necessary.

## Reproduce

```bash
.venv-macos/bin/python -m evaluation.frozen_benchmark_comparison \
  --output-dir results/architecture-comparison
```

The command refuses a non-empty output directory unless `--overwrite` is supplied. Before writing any result, it rejects a run whose normal-scenario IDs, 300-scenario count, frozen-input hashes, or oracle-metric schema differs from A0.

## Generated artifacts

| Artifact | Use |
| --- | --- |
| `TABLE_0_BENCHMARK_COMPOSITION.md` | Frozen scenario population composition. |
| `TABLE_1_SYSTEM_COMPARISON.md` | Overall architecture comparison. |
| `TABLE_2_KEY_ORACLE_ABLATIONS.md` | Selected independent-oracle rates. |
| `TABLE_3_CONTROLLED_FIXTURE_PROTOCOLS.md` | Conflict and integrity-fixture results. |
| `TABLE_4_CROP_STRATIFICATION.md` | Crop-level A0/A3/A5 comparison. |
| `TABLE_5_DISTRICT_STRATIFICATION.md` | Geographic supplementary comparison. |
| `oracle_metric_rates.csv` | All 19 normal-scenario oracle metrics, long form. |
| `crop_stratified_key_metrics.csv` | Complete crop × system × key-metric values. |
| `district_stratified_key_metrics.csv` | Complete district × system × key-metric values. |
| `benchmark_composition.csv` | Machine-readable frozen-population composition. |
| `FIGURE_*.png` / `FIGURE_*.pdf` | 300 dpi raster and vector paper figures. |
| `comparison_manifest.json` | Source artifact fingerprints, validation status, and generation Git state. |
