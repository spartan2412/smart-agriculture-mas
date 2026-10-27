# Registry Data Sources

This reference lists the public sources used to admit the frozen 30-site
IndiaAgriAlignBench registry. It covers the final benchmark only. The exact
query URL, retrieval time, and SHA-256 hash for each dynamic record remain in
the linked evidence CSVs so that this readable reference does not become a
second, divergent source of truth.

Use `final_study_sites.csv` and `source_scoped_final_site_admission.csv` as
the authoritative final-site records.

## Source-to-evidence map

| Evidence layer | Public source used | Exact website or API endpoint | Final registry record |
|---|---|---|---|
| District boundary | geoBoundaries, India ADM2 simplified boundary | [geoBoundaries IND ADM2 GeoJSON](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IND/ADM2/geoBoundaries-IND-ADM2_simplified.geojson) | `preflight_representative_cropland_cells.csv`: `district_geometry_url`, `district_geometry_sha256` |
| Representative cropland cell | ESA WorldCover 2021 class 40, accessed through Microsoft Planetary Computer | [Microsoft Planetary Computer data API](https://planetarycomputer.microsoft.com/api/data/v1/item/bbox/) | `preflight_representative_cropland_cells.csv`: `worldcover_raster_url`, `worldcover_raster_sha256`, `worldcover_item_id` |
| Historical weather | NASA POWER Daily Point API, AG community | [NASA POWER daily point endpoint](https://power.larc.nasa.gov/api/temporal/daily/point) | `preflight_nasa_power_fixed_window_weather.csv`: `official_url`, `response_sha256` |
| Static soil properties | ISRIC SoilGrids OGC WCS | [ISRIC map server](https://maps.isric.org/mapserv) | `preflight_soilgrids_wcs_profiles.csv`: `metadata_request_url`, `value_request_url`, `metadata_sha256`, `value_tiff_sha256` |
| Sentinel-2 scene metadata | Microsoft Planetary Computer Sentinel-2 L2A STAC catalog | [STAC search endpoint](https://planetarycomputer.microsoft.com/api/stac/v1/search) | `preflight_sentinel_scene_coverage.csv`: request-payload and response hashes, selected item ID, acquisition time, cloud and no-data metadata |
| Crop profile and sowing window | ICAR–CRIDA district Crop Contingency Plans | [ICAR–CRIDA CCP portal](https://icar-crida.res.in/CCP/) | `preflight_icar_crida_ccp_coverage.csv`: exact `crop_profile_url`, `sowing_window_url`, and document hashes |
| Historical same-crop mandi market evidence | Agmarknet 2.0 monthly wholesale-price API | [Agmarknet marketwise monthly endpoint](https://api.agmarknet.gov.in/v1/price-trend/wholesale-prices-monthly) | `preflight_agmarknet_historical_market_coverage.csv`: `official_url`, `payload_sha256`; the same URL is copied to `final_study_sites.csv` |
| Regional fertilizer and diagnosis-triggered protection evidence | State agricultural universities and ICAR crop advisories | Exact dated documents in the next table | `preflight_management_bundle_catalog.csv` and `regional_management_source_snapshot.csv` |
| Regulatory cross-check for chemical options | PPQS / CIBRC Major Uses of Pesticides records | Exact dated documents in the next table | `preflight_management_bundle_catalog.csv` and `regional_management_source_snapshot.csv` |

## Exact per-site request records

The following artifacts are the canonical location for every request URL. They
must be cited or reproduced from these files rather than recreated manually.

| Artifact | Exact-URL fields | Coverage |
|---|---|---|
| [`preflight_representative_cropland_cells.csv`](preflight_representative_cropland_cells.csv) | `district_geometry_url`, `worldcover_raster_url` | 30 documented representative cropland cells; 23 unique WorldCover raster requests |
| [`preflight_nasa_power_fixed_window_weather.csv`](preflight_nasa_power_fixed_window_weather.csv) | `official_url` | 30 fixed crop-season decision windows |
| [`preflight_soilgrids_wcs_profiles.csv`](preflight_soilgrids_wcs_profiles.csv) | `metadata_request_url`, `value_request_url` | Six 0–5 cm properties at each final cell |
| [`preflight_sentinel_scene_coverage.csv`](preflight_sentinel_scene_coverage.csv) | Endpoint shown above; `search_payload_sha256`, `response_sha256`, and `selected_item_id` | One quality-gated Sentinel-2 L2A scene per final cell/window |
| [`preflight_icar_crida_ccp_coverage.csv`](preflight_icar_crida_ccp_coverage.csv) | `crop_profile_url`, `sowing_window_url`, `pest_disease_contingency_url` | District CCP documents used for crop/season evidence |
| [`preflight_agmarknet_historical_market_coverage.csv`](preflight_agmarknet_historical_market_coverage.csv) | `official_url` | 30 exact crop × district × historical-month market reports |
| [`regional_management_source_snapshot.csv`](regional_management_source_snapshot.csv) | `official_url` | Dated official management and PPQS documents, with retrieval hashes |

## Final regional management and regulatory documents

Only the source IDs listed below are named by the final management bundles.
They provide regional baselines or diagnosis/threshold-triggered IPM options;
they are not farm-specific prescriptions or default spray calendars.

| Source ID | Provider and document | Applies to final bundle(s) | Exact official URL |
|---|---|---|---|
| `PAU_KHARIF_2026` | Punjab Agricultural University, *Package of Practices for Crops of Punjab — Kharif 2026* | Punjab rice: fertilizer baseline and diagnosis-triggered crop protection | [PDF](https://www.pau.edu/content/ccil/pf/pp_kharif.pdf) |
| `PAU_RABI_2025_26` | Punjab Agricultural University, *Package of Practices for Crops of Punjab — Rabi 2025–26* | Punjab wheat: fertilizer baseline and diagnosis-triggered crop protection | [PDF](https://pau.edu/content/ccil/pf/pp_rabi.pdf) |
| `ICAR_RABI_STATE_ADVISORIES_2021_22` | Indian Council of Agricultural Research, *Rabi Agro-Advisory for Farmers 2021–22* | Tamil Nadu maize and Maharashtra chickpea: crop/region-compatible fertilizer and IPM evidence | [PDF](https://icar.org.in/sites/default/files/2022-09/Rabi-Agro-Advisory-2021-22_0.pdf) |
| `TNAU_MAIZE_FAW_2023` | Tamil Nadu Agricultural University, *Fall armyworm management in maize* | Tamil Nadu maize: diagnosis-triggered fall-armyworm IPM action | [Web page](https://agritech.tnau.ac.in/crop_protection/maize/crop_prot_maize_fall_armyworm.html) |
| `ICAR_IISR_SOYBEAN_CENTRAL_ADVISORY_2024` | ICAR–Indian Institute of Soybean Research, *Weekly advisory for soybean farmers, 1–7 July 2024* | Madhya Pradesh and Rajasthan soybean: regional fertilizer/crop-establishment baseline | [PDF](https://icar-nsri.res.in/pdfdoc/Advisory2024/July,1-7th,2024.pdf) |
| `ICAR_IISR_SOYBEAN_BULLETIN_2023` | ICAR–Indian Institute of Soybean Research, *Improved Technologies and Recommendations for Maximizing Soybean Productivity* | Madhya Pradesh and Rajasthan soybean: diagnosis/ETL-triggered IPM evidence | [PDF](https://icar-nsri.res.in/pdfdoc/ExtensionBulletin2023E_2.pdf) |
| `TNAU_TOMATO_FERTIGATION_2014` | Tamil Nadu Agricultural University, *Tomato fertigation schedule for hybrids* | Tamil Nadu tomato: hybrid drip-fertigation baseline only | [PDF](https://agritech.tnau.ac.in/horticulture/ferti_schedule.pdf) |
| `TNAU_TOMATO_EARLY_BLIGHT_2023` | Tamil Nadu Agricultural University, *Tomato early-blight integrated disease management* | Tamil Nadu tomato: diagnosis-triggered early-blight action | [Web page](https://agritech.tnau.ac.in/crop_protection/tomato_diseases_2.html) |
| `CIBRC_INSECTICIDE_2026` | PPQS / CIBRC, *Major Uses of Pesticides — chemical insecticides* | Rice, maize, chickpea, and soybean crop–problem–formulation/rate cross-checks | [PDF](https://ppqs.gov.in/sites/default/files/updated_mup_insecticide_as_on_31.03.2026_c.pdf) |
| `CIBRC_FUNGICIDE_2026` | PPQS / CIBRC, *Major Uses of Pesticides — chemical fungicides* | Rice, wheat, and tomato crop–problem–formulation/rate cross-checks | [PDF](https://ppqs.gov.in/sites/default/files/2._chemical_mup_fungicide_as_on_31.03.2026_0.pdf) |

The document date, provider, applicable geography/crop scope, retrieval time,
and SHA-256 hash for each entry are in
[`regional_management_source_snapshot.csv`](regional_management_source_snapshot.csv).

## Paper-reference guidance

For the paper, cite the provider and dated source document or product, then
cite this repository artifact for the exact frozen request and hash. For
example: “NASA POWER Daily Point API, AG community, fixed request archived in
`preflight_nasa_power_fixed_window_weather.csv`.” Use the data artifact rather
than a generic homepage when reporting a result tied to a particular site and
decision window.

Do not describe ESA WorldCover cells as farmer parcels or crop-type-labelled
pixels. Do not convert a regional fertilizer source into a field-specific dose.
Do not present the 2026 PPQS/CIBRC records as historic registration evidence
for the 2025 scenarios; they are audit-time regulatory cross-checks.

## Downstream enrichment note

This source register documents admission evidence only. The fourth
post-harvest/storage/logistics enrichment is downstream of the frozen registry
and cannot revise a site admission or crop/location/season alignment. Its
separate provider records, raw snapshots, hashes, and permitted uses are in
[`../scenarios/enriched/DATA_SOURCES.md`](../scenarios/enriched/DATA_SOURCES.md)
and [`Documentation/DATA_SOURCES.md`](../../Documentation/DATA_SOURCES.md).
