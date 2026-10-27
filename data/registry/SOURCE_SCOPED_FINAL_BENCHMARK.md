# Source-Scoped Final Benchmark

`final_study_sites.csv` is the frozen, 30-site benchmark derived from
`source_scoped_preflight_pool.csv`. It is the registry's only study-site
manifest.

The final benchmark contains five district-scale scenarios for each crop:

| Crop | Final districts |
|---|---|
| Rice | Ludhiana, Patiala, Sangrur, Mansa, Bathinda (Punjab) |
| Wheat | Ludhiana, Patiala, Sangrur, Mansa, Bathinda (Punjab) |
| Maize | Coimbatore, Erode, Salem, Namakkal, Ariyalur (Tamil Nadu) |
| Chickpea | Jalna, Beed, Latur, Parbhani, Nanded (Maharashtra) |
| Soybean | Indore, Ujjain, Dewas (Madhya Pradesh); Jhalawar, Baran (Rajasthan) |
| Tomato | Krishnagiri, Dharmapuri, Salem, Dindigul, Coimbatore (Tamil Nadu) |

## Final admission result

`source_scoped_final_site_admission.csv` records **30/30 admitted** rows.
Each row passes all of these gates without borrowing a crop, market, or
management source from another location:

1. A documented representative cropland cell inside the geoBoundaries IND ADM2
   district polygon, selected deterministically from ESA WorldCover 2021 class
   40 (cropland).
2. A frozen crop-season month and an exact public Agmarknet 2.0 historical
   market report for the registered district and crop form. Rice uses the
   explicitly recorded `Paddy(Common)` market form.
3. Co-located NASA POWER daily weather for that frozen month.
4. All six declared 0–5 cm SoilGrids WCS properties at the same point.
5. A Sentinel-2 L2A scene in the same month meeting the declared cloud and
   no-data metadata rule.
6. Official crop/season evidence, a dated compatible regional fertilizer
   baseline, a dated diagnosis-triggered protection option, and the documented
   PPQS formulation/rate cross-check.
7. Retrieval timestamps, official URLs, and content hashes for the dynamic
   source artifacts.

## Scope that must remain explicit in the paper

This is a **district-scale, public-data benchmark**, not a set of surveyed
farms. ESA WorldCover confirms that the fixed point is cropland; it does not
label that individual point as rice, wheat, maize, chickpea, soybean, or
tomato. Crop identity is supported at district/covered-region level by the
separate official crop-season and same-district market evidence. No paper or
interface may describe these coordinates as farmer parcels.

Fertilizer schedules are regional fallbacks and do not replace a field soil
test. Protection records are diagnosis/threshold-triggered IPM options, never
default calendar sprays. The 2026 PPQS records are an audit-time regulatory
cross-check; they must not be presented as a historic registration assertion
for a 2025 scenario.

## Rebuild order

```bash
.venv-macos/bin/python scripts/collect_crida_ccp_evidence.py --sites data/registry/source_scoped_preflight_pool.csv --out data/registry/preflight_icar_crida_ccp_coverage.csv
.venv-macos/bin/python scripts/collect_agmarknet_historical_market_evidence.py --sites data/registry/source_scoped_preflight_pool.csv --out data/registry/preflight_agmarknet_historical_market_coverage.csv
.venv-macos/bin/python scripts/build_source_scoped_preflight_audit.py
.venv-macos/bin/python scripts/select_representative_cropland_cells.py
.venv-macos/bin/python scripts/collect_nasa_power_fixed_window_weather.py
.venv-macos/bin/python scripts/collect_soilgrids_wcs_profiles.py --sites data/registry/source_scoped_preflight_pool.csv --audit data/registry/preflight_representative_cropland_cells.csv --out data/registry/preflight_soilgrids_wcs_profiles.csv
.venv-macos/bin/python scripts/collect_sentinel_scene_coverage.py --sites data/registry/source_scoped_preflight_pool.csv --audit data/registry/preflight_representative_cropland_cells.csv --out data/registry/preflight_sentinel_scene_coverage.csv
.venv-macos/bin/python scripts/build_source_scoped_final_admission.py
```

The management-source snapshot and policy archive are versioned evidence. Do
not overwrite them during an ordinary rebuild: a changed official document,
source date, or PPQS record requires a new documented benchmark version and a
fresh admission audit.
