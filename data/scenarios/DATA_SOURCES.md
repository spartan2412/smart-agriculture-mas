# Scenario Data Sources

This is the reference list for the 300 source-gated scenario contexts in this
directory. It complements, rather than replaces, the frozen site-registry
reference at [`../registry/DATA_SOURCES.md`](../registry/DATA_SOURCES.md).

For a particular scenario, the authoritative provenance is its row in
[`manifests/scenario_manifest.csv`](manifests/scenario_manifest.csv), together
with the referenced raw payload under `raw/`. That row contains the exact
weather and market request URL, the raw file path, and SHA-256 checksums. It
should be cited instead of recreating a request manually.

## Sources used directly in scenario records

| Scenario evidence | Public provider and exact website/API | How it is retained |
|---|---|---|
| Daily weather | NASA POWER Daily Point API, AG community: [endpoint](https://power.larc.nasa.gov/api/temporal/daily/point) | `weather_source_url`, `weather_current_response_sha256`, and `weather_raw_path` in the manifest. Every query requests `T2M`, `PRECTOTCORR`, `RH2M`, and `WS2M` for the scenario cell and calendar month. |
| Historical crop--district market report | Agmarknet 2.0 marketwise monthly wholesale-price API: [endpoint](https://api.agmarknet.gov.in/v1/price-trend/wholesale-prices-monthly) | `market_source_url`, canonical JSON checksum, and `market_raw_path` in the manifest. The response title must name the source commodity, registered district, state, month, and year; it must contain at least one reported price. |
| Sentinel-2 scene metadata | Microsoft Planetary Computer, [Sentinel-2 L2A STAC search](https://planetarycomputer.microsoft.com/api/stac/v1/search) | The raw STAC response is in `raw/sentinel/`. The manifest retains the endpoint, request-payload checksum, response checksum, selected item ID, timestamp, cloud cover, and no-data percentage. Supplementary records require cloud <= 30% and no-data <= 10%. |
| Static soil profile | ISRIC SoilGrids OGC WCS: [map server](https://maps.isric.org/mapserv) | The fixed 0--5 cm properties for the same representative cell come from [`../registry/preflight_soilgrids_wcs_profiles.csv`](../registry/preflight_soilgrids_wcs_profiles.csv), including each exact metadata/value request URL and TIFF checksum. |

The 30 anchors retain their date-specific weather and market raw payloads.
The 270 supplementary scenarios retain date-specific weather, market, and
Sentinel raw payloads. The consolidated manifest states which kind of record
each row is.

## Sources used to align the scenario location and season

| Alignment evidence | Exact website/API | Frozen evidence artifact |
|---|---|---|
| District boundary | [geoBoundaries India ADM2 GeoJSON](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IND/ADM2/geoBoundaries-IND-ADM2_simplified.geojson) | [`../registry/preflight_representative_cropland_cells.csv`](../registry/preflight_representative_cropland_cells.csv): `district_geometry_url`, hash, and cell-selection method. |
| Representative cropland cell | ESA WorldCover 2021 class 40 through the [Microsoft Planetary Computer data API](https://planetarycomputer.microsoft.com/api/data/v1/item/bbox/) | The same artifact retains the exact WorldCover raster URL, item ID, and raster checksum for each final site. |
| Crop profile and declared season window | [ICAR--CRIDA District Crop Contingency Plan portal](https://icar-crida.res.in/CCP/) | [`../registry/preflight_icar_crida_ccp_coverage.csv`](../registry/preflight_icar_crida_ccp_coverage.csv): exact crop-profile, sowing-window, and contingency-document URLs and hashes. |

The location is a documented district-scale representative cropland cell. It
is not a surveyed farm or a crop-type-labelled field. Crop identity and season
membership are supported by the crop/season evidence plus the exact
crop--district market report; they are not inferred from the WorldCover pixel.

## Regional management and regulatory sources

These sources establish regional fertilizer baselines and diagnosis/threshold
conditions for possible crop-protection options. They do **not** create a
farm-specific NPK dose, disease finding, pesticide action, or spray schedule
in any scenario. The manifest therefore marks those claims as unavailable.

| Source ID | Provider/document | Exact official website |
|---|---|---|
| `PAU_KHARIF_2026` | Punjab Agricultural University, *Package of Practices for Crops of Punjab -- Kharif 2026* | [PDF](https://www.pau.edu/content/ccil/pf/pp_kharif.pdf) |
| `PAU_RABI_2025_26` | Punjab Agricultural University, *Package of Practices for Crops of Punjab -- Rabi 2025--26* | [PDF](https://pau.edu/content/ccil/pf/pp_rabi.pdf) |
| `ICAR_RABI_STATE_ADVISORIES_2021_22` | Indian Council of Agricultural Research, *Rabi Agro-Advisory for Farmers 2021--22* | [PDF](https://icar.org.in/sites/default/files/2022-09/Rabi-Agro-Advisory-2021-22_0.pdf) |
| `TNAU_MAIZE_FAW_2023` | Tamil Nadu Agricultural University, fall-armyworm management in maize | [Web page](https://agritech.tnau.ac.in/crop_protection/maize/crop_prot_maize_fall_armyworm.html) |
| `ICAR_IISR_SOYBEAN_CENTRAL_ADVISORY_2024` | ICAR--Indian Institute of Soybean Research, soybean advisory, 1--7 July 2024 | [PDF](https://icar-nsri.res.in/pdfdoc/Advisory2024/July,1-7th,2024.pdf) |
| `ICAR_IISR_SOYBEAN_BULLETIN_2023` | ICAR--Indian Institute of Soybean Research, *Improved Technologies and Recommendations for Maximizing Soybean Productivity* | [PDF](https://icar-nsri.res.in/pdfdoc/ExtensionBulletin2023E_2.pdf) |
| `TNAU_TOMATO_FERTIGATION_2014` | Tamil Nadu Agricultural University, tomato hybrid fertigation schedule | [PDF](https://agritech.tnau.ac.in/horticulture/ferti_schedule.pdf) |
| `TNAU_TOMATO_EARLY_BLIGHT_2023` | Tamil Nadu Agricultural University, tomato early-blight integrated disease management | [Web page](https://agritech.tnau.ac.in/crop_protection/tomato_diseases_2.html) |
| `CIBRC_INSECTICIDE_2026` | PPQS / CIBRC, *Major Uses of Pesticides -- chemical insecticides* | [PDF](https://ppqs.gov.in/sites/default/files/updated_mup_insecticide_as_on_31.03.2026_c.pdf) |
| `CIBRC_FUNGICIDE_2026` | PPQS / CIBRC, *Major Uses of Pesticides -- chemical fungicides* | [PDF](https://ppqs.gov.in/sites/default/files/2._chemical_mup_fungicide_as_on_31.03.2026_0.pdf) |

The official URL, retrieval time, SHA-256, provider, crop scope, geography,
and source-date checks for every management source are frozen in
[`../registry/regional_management_source_snapshot.csv`](../registry/regional_management_source_snapshot.csv).
The applicable crop/region bundle and locator are in
[`../registry/preflight_management_bundle_catalog.csv`](../registry/preflight_management_bundle_catalog.csv).

## Reproducibility and interpretation

- The manifest contains the full, exact NASA POWER and Agmarknet URL for every
  one of the 300 records. The source hash and raw payload let a reviewer check
  the downloaded content without assuming a generic endpoint is unchanged.
- Sentinel search is a POST request; its endpoint, deterministic query-payload
  hash, raw response, and selected quality-gated item are retained per
  supplementary scenario.
- Weather aggregates and market summary statistics in `processed/` are
  calculations from source values, not simulated measurements.
- A source-backed context is not a farm observation. Crop stage, disease event,
  farm fertilizer prescription, and crop-protection action remain explicit
  abstentions unless date- and site-compatible evidence is separately added.
- Fifteen tomato contexts are January--March 2026 records in the same declared
  rabi window as their December 2025 anchors. They are explicitly labelled
  `post_anchor_same_declared_season_historical_context` in the manifest; no
  source data after 2026-03-31 are used.

For paper citations, cite the provider/product or dated document above and
cite the scenario manifest plus raw-payload checksum for the exact record used
in a result.

The four additive enrichment layers do not alter these frozen scenario sources.
Their provider references, including the post-harvest/storage/logistics source
register, are documented in
[`enriched/DATA_SOURCES.md`](enriched/DATA_SOURCES.md) and the project-wide
[`Documentation/DATA_SOURCES.md`](../../Documentation/DATA_SOURCES.md).
