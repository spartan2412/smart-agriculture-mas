# Final Study-Site Registry

This directory contains the frozen, public-data benchmark for six Indian crops
across 30 district-scale study sites. It is an evidence registry, not a
collection of surveyed farms or crop-labelled field parcels.

## Study design

| Crop | Final districts | Sites |
|---|---|---:|
| Rice | Ludhiana, Patiala, Sangrur, Mansa, Bathinda (Punjab) | 5 |
| Wheat | Ludhiana, Patiala, Sangrur, Mansa, Bathinda (Punjab) | 5 |
| Maize | Coimbatore, Erode, Salem, Namakkal, Ariyalur (Tamil Nadu) | 5 |
| Chickpea | Jalna, Beed, Latur, Parbhani, Nanded (Maharashtra) | 5 |
| Soybean | Indore, Ujjain, Dewas (Madhya Pradesh); Jhalawar, Baran (Rajasthan) | 5 |
| Tomato | Krishnagiri, Dharmapuri, Salem, Dindigul, Coimbatore (Tamil Nadu) | 5 |
| **Total** |  | **30** |

Every final site is keyed by `site_id × crop × season × fixed decision
window`. The final manifest is fixed until an explicitly versioned successor
benchmark is created.

## Authoritative files

- `final_study_sites.csv` is the frozen 30-site benchmark manifest. Use this
  file as the input to scenario generation, MAS runs, baselines, and paper
  evaluation.
- `source_scoped_final_site_admission.csv` is the final admission decision.
  All 30 rows are `admitted` and every evidence gate is `pass`.
- `SOURCE_SCOPED_FINAL_BENCHMARK.md` defines the admission method, public
  sources, limitations, and rebuild sequence.
- `DATA_SOURCES.md` is the paper-ready reference list of public providers,
  exact official websites, and the artifact containing each frozen request.

## Evidence retained for each final site

- `source_scoped_preflight_pool.csv` and
  `source_scoped_preflight_audit.csv` record the source-scoped selection and
  prerequisite-gate audit.
- `preflight_representative_cropland_cells.csv` records the deterministic ESA
  WorldCover cropland cell inside the matching geoBoundaries district.
- `preflight_nasa_power_fixed_window_weather.csv`,
  `preflight_soilgrids_wcs_profiles.csv`, and
  `preflight_sentinel_scene_coverage.csv` provide co-located weather, static
  soil, and Sentinel-2 metadata evidence for the frozen window.
- `preflight_icar_crida_ccp_coverage.csv` and
  `preflight_agmarknet_historical_market_coverage.csv` provide crop-season
  and same-crop, same-district historical market evidence.
- `preflight_management_bundle_catalog.csv` defines the compatible regional
  fertilizer baseline, diagnosis-triggered protection source, and PPQS
  cross-check for each crop/region bundle.
- `regional_management_source_snapshot.csv` and
  `regional_management_policy.csv` retain the dated official source hashes and
  detailed management records. Only source IDs named by the final management
  bundle catalog are part of the final benchmark.

## Interpretation rules

- Coordinates identify documented representative cropland cells, not farm
  parcels and not crop-type-labelled pixels.
- Crop identity is supported at district or covered-region level by official
  crop-season evidence and the exact same-district market report.
- Fertilizer records are regional fallbacks. They do not replace a field soil
  test or justify a farm-specific NPK prescription.
- Protection records are diagnosis/threshold-triggered IPM options. They are
  never default calendar sprays.
- The 2026 PPQS/CIBRC records are audit-time regulatory cross-checks. They
  must not be described as historic registration assertions for a 2025
  scenario.

For the full method and reproducible collection order, read
`SOURCE_SCOPED_FINAL_BENCHMARK.md`.

## Downstream benchmark boundary

The registry remains frozen after admission. The four downstream enrichment
layers—including the post-harvest/storage/logistics layer—do not change a final
site, its crop/season claim, or any registry evidence gate. They are joined at
runtime only by the fail-closed benchmark loader after their own source, hash,
identity, and scope checks pass. See
[`../scenarios/enriched/README.md`](../scenarios/enriched/README.md) and the
project-wide [`Documentation/DATA_SOURCES.md`](../../Documentation/DATA_SOURCES.md).

The separate
[`conflict_fixture_registry`](../conflict_fixture_registry/README.md) also
never changes this registry. Its 60 records reuse a real base scenario only to
test the resolver and integrity policies with labelled in-memory overlays; they
are evaluation fixtures, not new study sites or agricultural evidence.

The external oracle evaluates a completed downstream MAS trace against the
immutable scenario bundle derived from this registry. It cannot relax an
admission gate or modify this registry. See the project-wide
[evaluation policy](../../Documentation/EVALUATION_POLICY.md) and
[oracle evaluation guide](../../Documentation/ORACLE_EVALUATION_GUIDE.md).
