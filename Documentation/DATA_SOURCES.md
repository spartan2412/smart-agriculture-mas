# Project Data Sources

This is the final, self-contained readable source reference for the frozen
30-site registry, 300-scenario benchmark, first enrichment, second enrichment,
regional-operation-plan enrichment, fourth post-harvest/storage/logistics
enrichment, recovery-operation evidence, and official RAG corpus. It contains the project’s source notes, exact public provider
links, source-use restrictions, and every admitted generic RAG document.

The CSV artifacts mentioned below preserve immutable per-record request URLs,
retrieval timestamps, raw payload paths, and SHA-256 hashes. They are audit
evidence, not additional source notes that must be consulted to understand what
data was used.

For a particular final site, scenario, enrichment row, RAG document, or
operation, cite the linked canonical artifact rather than recreating a source
request manually.

## Evaluation implementation note

The oracle evaluation framework adds **no new public agricultural source,
document, API call, or scenario evidence**. It is a read-only internal check
over the frozen artifacts already listed in this register: scenario identity,
source URLs/hashes, RAG scope, action bindings, plan items, capability
restrictions, and controlled fixture metadata. Its policy boundary is in
[`EVALUATION_POLICY.md`](EVALUATION_POLICY.md), and its complete check-to-
artifact mapping is in
[`ORACLE_EVALUATION_GUIDE.md`](ORACLE_EVALUATION_GUIDE.md).

Because the normal 300-scenario population contains only records that passed
these documented source, identity, scope, and hash gates before it was frozen,
a 100% A0 structural-conformance rate is expected when the complete
deterministic system preserves those same restrictions. This does not turn the
listed sources into independent farm-outcome labels or make the rate an
agricultural-accuracy measure.

The completed A0–A6 architecture comparison likewise adds no new public
source, scenario, enrichment, or agricultural label. It reads only persisted
benchmark and fixture outputs, first verifies that every system used the same
300 scenario IDs and frozen-input hashes, and then writes derived tables and
figures. Its input-artifact SHA-256 values and generation metadata are in
[`results/v2_2-phase7-controlled-comparison/architecture-ablation/comparison_manifest.json`](../results/v2_2-phase7-controlled-comparison/architecture-ablation/comparison_manifest.json).
The comparison is an internal evaluation artifact, not a new data provider or
evidence layer.

### Phase 7 completion note

The final E0/E1-v5 controlled comparison also adds **no public agricultural
source, scenario, enrichment, RAG passage, or label**. It reads only the
already-listed persisted E0/A0, E1-v5/A0, held-out relevance, architecture
ablation, and fixture artifacts. Its complete source-artifact hashes and
generation metadata are in
[`results/v2_2-phase7-controlled-comparison/phase7_comparison_manifest.json`](../results/v2_2-phase7-controlled-comparison/phase7_comparison_manifest.json).
The Ollama/Metal runtime record is reproducibility metadata, not an
agricultural evidence provider. The final held-out result and six paired
farmer-message examples likewise do not alter this source register.

The bounded-LLM relevance evaluations likewise add no external provider or
new agricultural observation. The observed E1-v4 set, the v5.1
development-only set, and the final v5.1 held-out set each derive their 96
question records solely from the already cited frozen scenario, enrichment,
RAG, operation-plan, and post-harvest artifacts. The final set additionally
locks its acceptance criteria and forbids overlap with both earlier sets at
scenario and study-site level. Its manifest stores SHA-256 values for each
consumed input and the frozen v5 runtime artifacts. See
[`BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md`](BOUNDED_LLM_V5_HELDOUT_PROTOCOL.md).

## Source-to-evidence map

| Evidence layer | Public source used | Exact website or API endpoint | Canonical project record |
|---|---|---|---|
| District boundary | geoBoundaries India ADM2 simplified boundary | [geoBoundaries IND ADM2 GeoJSON](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IND/ADM2/geoBoundaries-IND-ADM2_simplified.geojson) | `data/registry/preflight_representative_cropland_cells.csv`: `district_geometry_url`, `district_geometry_sha256` |
| Representative cropland cell | ESA WorldCover 2021 class 40 through Microsoft Planetary Computer | [Microsoft Planetary Computer data API](https://planetarycomputer.microsoft.com/api/data/v1/item/bbox/) | `data/registry/preflight_representative_cropland_cells.csv`: `worldcover_raster_url`, `worldcover_raster_sha256`, `worldcover_item_id` |
| Registry/scenario weather | NASA POWER Daily Point API, AG community | [NASA POWER daily point endpoint](https://power.larc.nasa.gov/api/temporal/daily/point) | Registry: `preflight_nasa_power_fixed_window_weather.csv`; scenarios: `scenario_manifest.csv`: `weather_source_url`, hash, and raw path |
| Static soil profile | ISRIC SoilGrids OGC WCS | [ISRIC map server](https://maps.isric.org/mapserv) | `data/registry/preflight_soilgrids_wcs_profiles.csv`: exact metadata/value request URLs and TIFF hashes |
| Registry/scenario Sentinel metadata | Microsoft Planetary Computer Sentinel-2 L2A STAC | [STAC search endpoint](https://planetarycomputer.microsoft.com/api/stac/v1/search) | Registry: `preflight_sentinel_scene_coverage.csv`; scenarios: manifest query/response hashes, selected item ID, timestamp, cloud, and no-data fields |
| Crop profile and declared season window | ICAR–CRIDA District Crop Contingency Plans | [ICAR–CRIDA CCP portal](https://icar-crida.res.in/CCP/) | `data/registry/preflight_icar_crida_ccp_coverage.csv`: exact crop-profile, sowing-window, and contingency-document URLs/hashes |
| Historical same-crop mandi evidence | Agmarknet 2.0 marketwise monthly wholesale-price API | [Agmarknet monthly endpoint](https://api.agmarknet.gov.in/v1/price-trend/wholesale-prices-monthly) | Registry: `preflight_agmarknet_historical_market_coverage.csv`; scenarios: manifest `market_source_url`, hash, and raw path |
| Regional fertilizer and conditional crop-protection context | PAU, TNAU, ICAR, IISR official documents | Exact dated documents listed below | `data/registry/preflight_management_bundle_catalog.csv` and `regional_management_source_snapshot.csv` |
| Regulatory chemical cross-check | PPQS / CIBRC Major Uses of Pesticides | Exact dated documents listed below | `data/registry/preflight_management_bundle_catalog.csv` and `regional_management_source_snapshot.csv` |
| First-enrichment water context | NASA POWER Daily API, AG community | [NASA POWER Daily API documentation](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) | `data/scenarios/enriched/nasa_power_water_context_features.csv`, manifest, status, and source-hashed raw responses |
| First-enrichment representative-cell NDVI | Microsoft Planetary Computer Sentinel-2 L2A STAC | [Sentinel-2 L2A collection](https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a) | Enriched Sentinel feature/status files and source-hashed raw STAC/COG evidence |
| First-enrichment market comparison | Agmarknet exact frozen monthly reports | [Agmarknet monthly endpoint](https://api.agmarknet.gov.in/v1/price-trend/wholesale-prices-monthly) | `data/scenarios/enriched/agmarknet_embedded_market_context_features.csv` and status/manifest files |
| Initial official action-RAG documents | PAU, TNAU, ICAR, IISR, PPQS/CIBRC | Exact documents listed below | `data/scenarios/enriched/official_rag_source_inventory.csv` and `official_rag_corpus_catalog.csv` |
| Dated soybean advisory RAG | ICAR–Indian Institute of Soybean Research weekly archives | [Archive index](https://icar-nsri.res.in/Advisory.html); [2021](https://icar-nsri.res.in/Advisory2021.html), [2022](https://icar-nsri.res.in/Advisory2022.html), [2023](https://icar-nsri.res.in/Advisory2023.html), [2024](https://icar-nsri.res.in/Advisory2024.html) | `expanded_official_rag_source_inventory.csv` and `official_rag_corpus_catalog.csv`: exact PDF URL, issue week, hash, and scope decision |
| Historical district RAG context | ICAR–CRIDA crop-profile, sowing-window, and contingency PDFs | [ICAR–CRIDA CCP portal](https://icar-crida.res.in/CCP/) | `official_rag_corpus_catalog.csv`, `ICAR_CRIDA_*` records: exact PDF URL, hash, crop/district scope, and restriction |
| Exact-week soybean operation extraction | ICAR–IISR advisory archives | [2023 archive](https://icar-nsri.res.in/Advisory2023.html) and [2024 archive](https://icar-nsri.res.in/Advisory2024.html) | `exact_week_iisr_action_records.csv`, `scenario_exact_week_iisr_action_bindings.csv`, and combined action views |
| Recovered historical Punjab-rice operations | Punjab Agricultural University annual Kharif packages, preserved at the Internet Archive | Official [PAU URL](https://www.pau.edu/content/ccil/pf/pp_kharif.pdf); replay copies [2023](https://web.archive.org/web/20230918105856id_/https://www.pau.edu/content/ccil/pf/pp_kharif.pdf), [2024](https://web.archive.org/web/20240830235813id_/https://www.pau.edu/content/ccil/pf/pp_kharif.pdf), [2025](https://web.archive.org/web/20250626143125id_/https://www.pau.edu/content/ccil/pf/pp_kharif.pdf) | `archived_pau_kharif_source_inventory.csv`, action/binding CSVs and audit: original URL, replay URL, capture time, PDF-year check, raw/extracted hash, quote and conservative time gate |
| Recovered historical Punjab-wheat operations | Punjab Agricultural University annual Rabi packages, preserved at the Internet Archive | Official [PAU Rabi URL](https://pau.edu/content/ccil/pf/pp_rabi.pdf); replay copies [2021–22](https://web.archive.org/web/20220108015141id_/https://www.pau.edu/content/ccil/pf/pp_rabi.pdf), [2023–24](https://web.archive.org/web/20230918105852id_/https://www.pau.edu/content/ccil/pf/pp_rabi.pdf), [2024–25](https://web.archive.org/web/20250523045635id_/https://pau.edu/content/ccil/pf/pp_rabi.pdf) | `archived_pau_rabi_source_inventory.csv`, action/binding CSVs and audit: original URL, replay URL, archive capture, original-server `Last-Modified`, PDF-year check, raw/extracted hash, quote and conservative time gate |
| Maharashtra chickpea technical operation | Mahatma Phule Krishi Vidyapeeth, Rahuri (MPKV) *Krishi Darshani 2023* | [MPKV extension-publication page](https://mpkv.ac.in/Extension/ExtensionPublication) and [official PDF](https://mpkv.ac.in/Uploads/Publication/Krishi%20Darshani%20%202023_20230607043125.pdf) | `mpkv_chickpea_source_inventory.csv`, action/binding CSVs and audit: original-PDF hash, original-server `Last-Modified` (`2023-06-07T11:01:25Z`), cited-page raster hashes, limited visual transcription, state/crop/season/date scope, and maturity/dryness gate |
| Public district/KVK advisory availability | ICAR KVK and IMD GKMS portals | [ICAR KVK portal](https://kvk.icar.gov.in/) and [IMD GKMS](https://agromet.imd.gov.in/) | `public_district_kvk_advisory_discovery.csv` and scenario status. No exact crop/district/date advisory was admitted. |

## Exact per-record provenance artifacts

These are the authoritative locations for all request URLs, hashes, source
dates, raw payload paths, and source-scope decisions.

| Project layer | Artifact | Exact source/provenance fields | Coverage |
|---|---|---|---|
| Registry | [`final_study_sites.csv`](../data/registry/final_study_sites.csv) | Final source IDs and evidence links | 30 admitted crop × district × season sites |
| Registry | [`source_scoped_final_site_admission.csv`](../data/registry/source_scoped_final_site_admission.csv) | Per-gate pass/fail and source references | 30/30 admitted sites |
| Registry | [`preflight_representative_cropland_cells.csv`](../data/registry/preflight_representative_cropland_cells.csv) | `district_geometry_url`, `worldcover_raster_url`, hashes | 30 representative cropland cells |
| Registry | [`preflight_nasa_power_fixed_window_weather.csv`](../data/registry/preflight_nasa_power_fixed_window_weather.csv) | `official_url`, response hash | 30 fixed decision windows |
| Registry | [`preflight_soilgrids_wcs_profiles.csv`](../data/registry/preflight_soilgrids_wcs_profiles.csv) | Metadata/value request URLs, metadata/TIFF hashes | Six 0–5 cm properties for each final cell |
| Registry | [`preflight_sentinel_scene_coverage.csv`](../data/registry/preflight_sentinel_scene_coverage.csv) | STAC request/response hashes, item ID, acquisition time, cloud/no-data | One quality-gated scene per final cell/window |
| Registry | [`preflight_icar_crida_ccp_coverage.csv`](../data/registry/preflight_icar_crida_ccp_coverage.csv) | Crop-profile, sowing-window, contingency URLs/hashes | Crop/season evidence for final sites |
| Registry | [`preflight_agmarknet_historical_market_coverage.csv`](../data/registry/preflight_agmarknet_historical_market_coverage.csv) | `official_url`, payload hash | 30 exact crop × district × month reports |
| Scenarios | [`scenario_manifest.csv`](../data/scenarios/manifests/scenario_manifest.csv) | Weather/market URLs, hashes, raw paths; Sentinel query/response hashes and selected scene metadata | 300 source-gated scenarios |
| Scenarios | [`scenario_features.csv`](../data/scenarios/processed/scenario_features.csv) | Source-derived feature values | 300 scenarios |
| Scenarios | [`scenario_evidence_status.csv`](../data/scenarios/evidence/scenario_evidence_status.csv) | Required abstentions and management-evidence status | 300 scenarios |
| First enrichment | [`mas_enrichment_contract.csv`](../data/scenarios/enriched/mas_enrichment_contract.csv) | Per-scenario allowed uses, required abstentions, and source artifact pointers | 300 scenarios |
| First enrichment | [`nasa_power_water_context_manifest.csv`](../data/scenarios/enriched/nasa_power_water_context_manifest.csv) | Exact request, raw path, and response hash | 300 historical water-context records |
| First enrichment | [`sentinel_ndvi_context_manifest.csv`](../data/scenarios/enriched/sentinel_ndvi_context_manifest.csv) | Frozen/recovered item and raw source references | Satellite context and preserved abstentions |
| First enrichment | [`agmarknet_embedded_market_context_manifest.csv`](../data/scenarios/enriched/agmarknet_embedded_market_context_manifest.csv) | Frozen report/hash and source-published comparison fields | 293 available, 7 unavailable comparisons |
| Second enrichment | [`official_rag_corpus_catalog.csv`](../data/scenarios/enriched/official_rag_corpus_catalog.csv) | Title, provider, exact official URL, period, raw hash, crop/geography scope, restriction | **All 92 admitted RAG documents** |
| Second enrichment | [`official_rag_corpus_all_chunks.csv`](../data/scenarios/enriched/official_rag_corpus_all_chunks.csv) | Chunk text, source URL, raw hash, locator | 4,582 provenance-carrying chunks |
| Second enrichment | [`scenario_official_rag_scope_all.csv`](../data/scenarios/enriched/scenario_official_rag_scope_all.csv) | Mandatory metadata decision before retrieval | 27,600 scenario × source scope rows |
| Second enrichment | [`official_action_records_all.csv`](../data/scenarios/enriched/official_action_records_all.csv) | Verbatim quote, page/section, source URL/hash, conditions | 41 source-quoted operation records |
| Second enrichment | [`scenario_official_action_bindings_all.csv`](../data/scenarios/enriched/scenario_official_action_bindings_all.csv) | Per-scenario action applicability/block reason | 12,300 scenario × action rows |
| Historical PAU operation recovery | [`archived_pau_kharif_source_inventory.csv`](../data/scenarios/enriched/archived_pau_kharif_source_inventory.csv), [`ARCHIVED_PAU_KHARIF_ACTION_AUDIT.md`](../data/scenarios/enriched/ARCHIVED_PAU_KHARIF_ACTION_AUDIT.md) | Official original URL plus transparent archive replay, capture timestamp, PDF-year check, hashes, quote and scope gate | 3 preserved PAU packages; 6 actions; 68 valid-but-stage-conditional bindings |
| MPKV Maharashtra chickpea operation recovery | [`mpkv_chickpea_source_inventory.csv`](../data/scenarios/enriched/mpkv_chickpea_source_inventory.csv), [`MPKV_CHICKPEA_ACTION_AUDIT.md`](../data/scenarios/enriched/MPKV_CHICKPEA_ACTION_AUDIT.md) | Original official PDF hash, exact cited-page raster hashes, limited visual transcription, source quote, date/state/crop/season scope, and field-condition gate | One state-extension technical operation; 50 valid-but-stage/dryness-conditional bindings |
| Second enrichment | [`expanded_official_rag_source_inventory.csv`](../data/scenarios/enriched/expanded_official_rag_source_inventory.csv) | Candidate URL, discovery URL, hash, status, and rejection reason | All IISR/CRIDA source discovery candidates |
| Second enrichment | [`public_district_kvk_advisory_discovery.csv`](../data/scenarios/enriched/public_district_kvk_advisory_discovery.csv) | Official access endpoint and public-access/scope result | District/KVK availability check |
| Second enrichment | [`sentinel_ndvi_timeseries_manifest.csv`](../data/scenarios/enriched/sentinel_ndvi_timeseries_manifest.csv) | Pre-decision STAC evidence and source references | 90-day NDVI chronology plan |
| Regional operation-plan enrichment | [`regional_operation_plan_summary.csv`](../data/scenarios/enriched/regional_operation_plan_summary.csv), [`regional_operation_plan_items.csv`](../data/scenarios/enriched/regional_operation_plan_items.csv), [`regional_operation_plan_provenance.csv`](../data/scenarios/enriched/regional_operation_plan_provenance.csv) | Projection of existing ICAR--CRIDA calendar, verified management-policy, and source-quoted-operation artifacts into traceable planning items; canonical source-input hashes | 300 scenario summaries; 1,507 source-linked items; no direct farm action |
| Fourth enrichment: post-harvest/storage/logistics | [`scenario_postharvest_logistics_context.csv`](../data/scenarios/enriched/scenario_postharvest_logistics_context.csv), [`scenario_postharvest_plan_items.csv`](../data/scenarios/enriched/scenario_postharvest_plan_items.csv), [`postharvest_source_inventory.csv`](../data/scenarios/enriched/postharvest_source_inventory.csv), [`postharvest_logistics_provenance.csv`](../data/scenarios/enriched/postharvest_logistics_provenance.csv) | Crop-scoped source-quoted handling references plus collection-date facility/warehouse/route context; all raw snapshots and derived records are hash-linked | 300 contexts; 700 conditional plan items; 14 exact-crop RAG passages; no direct farm action, booking, dispatch, freight, or availability claim |
| Evaluation-only conflict fixtures | [`conflict_fixture_manifest.csv`](../data/conflict_fixture_registry/conflict_fixture_manifest.csv), [`fixtures/`](../data/conflict_fixture_registry/fixtures/), and [`CONFLICT_FIXTURE_AUDIT.md`](../data/conflict_fixture_registry/CONFLICT_FIXTURE_AUDIT.md) | Real base-scenario identity plus existing source-reference metadata; a labelled in-memory overlay carries no new agricultural observation or external document | 60 controlled policy cases across all 30 final crop--location sites; never loaded by a normal farmer-facing run |
| Evaluation-only provenance/alignment fixtures | [`provenance_fixture_manifest.csv`](../data/provenance_fixture_registry/provenance_fixture_manifest.csv), [`fixtures/`](../data/provenance_fixture_registry/fixtures/), and [`PROVENANCE_FIXTURE_AUDIT.md`](../data/provenance_fixture_registry/PROVENANCE_FIXTURE_AUDIT.md) | Real frozen scenario identity, regional-plan row, and loader-payload metadata; one labelled in-memory mismatch per case, with no new agricultural observation or external document | 60 controlled integrity cases across all 30 final crop--location sites; never loaded by a normal workflow |
| Derived result and paper-presentation outputs | [`results/v2_2-phase7-controlled-comparison`](../results/v2_2-phase7-controlled-comparison/) and [`results/v2_2-paper-artifacts`](../results/v2_2-paper-artifacts/) | Persisted v2.2 E0/A1–A6 aggregate/stratified reports plus fixture results; Phase 10 regenerates tables, figures, cases, and the E2/E3 transfer-negative-result table only from frozen inputs, saved results, and the agent contract. Each package has an input/output SHA-256 manifest. | Architecture comparisons plus ten presentation tables, four PNG/PDF figures, and source-traceable case studies; no new public source, scenario, farm observation, or agricultural evidence |

## Source notes by project layer

### Frozen 30-site registry

- geoBoundaries supplies the district boundary; ESA WorldCover supplies a
  class-40 representative cropland cell inside it. Neither source identifies a
  farmer’s parcel or the crop growing at that cell.
- ICAR–CRIDA documents support the declared crop and seasonal window. The
  district crop-profile, sowing-window, and contingency document URLs and
  hashes are retained for every final site.
- NASA POWER provides complete daily historical weather for the fixed cell and
  decision window. SoilGrids provides six static 0–5 cm soil predictors. These
  are geographically aligned contextual sources, not a live weather forecast,
  sensor reading, soil-moisture observation, or field soil test.
- A Sentinel-2 L2A item must satisfy the declared metadata-quality gate. An
  Agmarknet monthly report must name the matching commodity, district, state,
  month, and year and have a reported price before the final site is admitted.
- Final management documents are linked as regional fertilizer/IPM evidence.
  PPQS/CIBRC records are audit-time regulatory cross-checks, not historical
  registration proof for an earlier scenario date or a treatment instruction.

### Frozen 300-scenario benchmark

- The benchmark contains 30 anchors and 270 supplementary historical records.
  Every supplementary record passes the same site, crop, declared-season,
  weather, market, and Sentinel metadata gates for its own calendar month.
- Every record has a NASA POWER weather response, an exact Agmarknet report,
  and raw source references; supplementary records also have a same-month
  Sentinel STAC response. Derived weather aggregates and market summaries are
  calculations from those source values, never simulated measurements.
- The static SoilGrids profile and the regional management bundle are inherited
  only from the same frozen final site. Missing evidence is never borrowed from
  another district, crop, or date.
- Crop stage, disease event, field N/P/K, farm fertilizer dose, pesticide or
  insecticide action, and aligned leaf imagery are not source observations in
  any of the 300 records. Their abstention status is deliberate.
- Fifteen tomato records use January–March 2026 data in the same declared rabi
  window as their December 2025 anchors. They are explicitly marked
  `post_anchor_same_declared_season_historical_context`; no scenario uses data
  after 2026-03-31.

### First enrichment

- NASA POWER is queried for the exact historical scenario window with
  temperature, precipitation, humidity, wind, radiation, modelled top/root-zone
  wetness, and land-evaporation variables. The resulting water context is
  retrospective representative-cell context only; it cannot issue an
  irrigation dose or reconstruct a decision-time forecast.
- Sentinel NDVI is calculated only from source-verified B04/B08/SCL point
  reads after item, cloud/no-data, coordinate, and clear-pixel checks. The
  bounded recovery can use only a qualifying candidate already present in the
  frozen same-month STAC search; it does not replace the frozen selected scene
  or create a crop/field label.
- The market comparison uses columns already published inside the exact frozen
  Agmarknet report. The public bulk lookback experiment encountered rate-limit
  and temporary-service responses, so it is not a MAS input. Seven unavailable
  comparison records remain explicit unavailable values.
- SoilGrids and the final management-source bundle are carried into the
  enrichment contract only as static/regional context. The 300-row
  `mas_enrichment_contract.csv` keeps irrigation action, farm-specific
  fertilizer prescription, treatment order, diagnosis, stage, and leaf vision
  outside the evidence permitted by the scenario.

### Second enrichment and official RAG

- The initial RAG collector admits a source only if retrieved bytes reproduce
  its frozen registry SHA-256. It extracts page/section text and rejects a
  source outside the scenario crop, registry geography, effective window, or
  allowed source role before retrieval ranking.
- The expansion begins with the official IISR 2021–2024 advisory archives and
  final-site ICAR–CRIDA documents. From 120 candidates, 78 documents are
  admitted: 27 dated IISR weekly PDFs and 51 CRIDA district PDFs. Forty-one
  weekly PDFs fail scope verification, one source is unavailable, and four
  archive links are malformed/ambiguous; none of them enters the corpus.
- The 92 admitted documents yield 4,582 provenance-carrying chunks and 27,600
  scenario × source metadata-scope decisions. IISR weekly sources require the
  stated soybean/zone/exact-week match. CRIDA sources are historical
  crop/district context only, not current advisories.
- Every structured operation quote is checked against its source page. The
  41-action catalog and 12,300 scenario-action binding matrix retain each
  condition and block reason. The two exact-week IISR PDFs yield 13 operations
  or guardrails and 57 conditional bindings, but zero automatic farm actions.
- Three Kharif annual PDFs from PAU's own URL were recovered through public
  archive-preservation replays for 2023–2025. Their self-identified year,
  original URL, replay URL, capture time, raw/extracted hashes and page-11
  quotations are recorded. They contribute six Punjab-rice operations and 68
  additional time-valid, crop-maturity-conditional bindings; they do not
  replace a scenario or enter the RAG corpus as a different publisher.
- MPKV Rahuri's dated 2023 *Krishi Darshani* adds one Maharashtra chickpea
  hard-pod harvest operation and 50 date/state/crop/season-scoped bindings.
  Its legacy Marathi font is not trusted for Unicode extraction: the original
  PDF and two exact cited-page rasters are hash frozen, with a deliberately
  limited visual transcription for the source quote. It remains conditional on
  observed maturity and crop dryness, and is a technical guide rather than a
  weekly/district advisory.
- Official KVK and IMD GKMS access was checked. No public exact
  crop + district + decision-date advisory passed the gates (0/300). The KVK
  portal was unavailable from the collection environment and the IMD entry was
  login-gated; a zone/state/static document is never relabelled as district
  advice.
- The 90-day pre-decision Sentinel chronology contains only source-hashed,
  quality-gated scene attempts and clear B04/B08 observations. Its numerical
  divergence candidates are evaluation context, not disease/stress labels or
  action triggers.

### Runtime access and RAG boundary

- `FrozenBenchmarkLoader` loads the complete source-linked regional plan,
  plan-input provenance, applicable action binding, and relevant recovery
  inventory into each immutable scenario runtime bundle. All 300 scenarios
  therefore have their seasonal, nutrient-policy, and IPM-policy plan items
  available to the benchmark MAS.
- The generic official RAG collection remains exactly the 92 admitted documents
  and 4,582 provenance-carrying chunks. It is filtered by the scenario RAG
  scope matrix before ranking; a document is not retrievable merely because it
  is present in project storage.
- Recovered PAU/MPKV PDFs are not added to that generic collection. A
  source-quoted passage from any recovered operation is made available only
  through the corresponding regional-plan item after crop, geography, season,
  and source-time action gates pass. This source-scoped path is available for
  229 scenarios; recovered PAU/MPKV source provenance is loaded and verified
  for the 99 scenarios that use it.
- These rules preserve access to valid historical operations while preventing
  cross-crop, cross-region, or out-of-date retrieval. They do not turn a
  regional operation into a farm-specific instruction.

## Fourth enrichment: post-harvest, storage, and logistics

The fourth enrichment keeps two evidence classes separate. Crop-handling
documents provide source-quoted technical references only after an exact crop
match; facility, warehouse, and route records are captured public-directory
context only. None reports the historical/current state of a harvested lot,
commodity acceptance, facility capacity/vacancy, booking, vehicle/freight,
dispatch, or a sell/hold outcome. The loader validates the source inventory,
raw files, hashes, crop/profile/item joins, candidate references, and RAG scope
before exposing a scenario-specific slice to the MAS.

| Source ID(s) | Provider and record | Exact public source | Permitted use in this project |
|---|---|---|---|
| `PAU_KHARIF_2026` | Punjab Agricultural University, *Package of Practices for Crops of Punjab — Kharif 2026* | [PDF](https://www.pau.edu/content/ccil/pf/pp_kharif.pdf) | Source-quoted rice handling only, conditional on observed maturity/lot condition. |
| `PAU_RABI_2025_26` | Punjab Agricultural University, *Package of Practices for Crops of Punjab — Rabi 2025–26* | [PDF](https://pau.edu/content/ccil/pf/pp_rabi.pdf) | Source-quoted wheat handling only, conditional on observed maturity/moisture. |
| `ICAR_RABI_STATE_ADVISORIES_2021_22` | Indian Council of Agricultural Research, *Rabi Agro-Advisory for Farmers 2021–22* | [PDF](https://icar.org.in/sites/default/files/2022-09/Rabi-Agro-Advisory-2021-22_0.pdf) | Source-quoted maize handling only, conditional on observed husk/lot moisture. |
| `MPKV_KRISHI_DARSHANI_2023` | Mahatma Phule Krishi Vidyapeeth, *Krishi Darshani 2023* | [PDF](https://mpkv.ac.in/Uploads/Publication/Krishi%20Darshani%20%202023_20230607043125.pdf) | Source-quoted chickpea handling only, conditional on hard pods and crop dryness. |
| `ICAR_IISR_SOYBEAN_BULLETIN_2023` | ICAR–Indian Institute of Soybean Research, *Improved Technologies and Recommendations for Maximizing Soybean Productivity* | [PDF](https://icar-nsri.res.in/pdfdoc/ExtensionBulletin2023E_2.pdf) | Source-quoted soybean handling only, conditional on observed maturity/harvest configuration. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20230925` | ICAR–IISR weekly soybean advisory, 25 Sep–01 Oct 2023 | [PDF](https://icar-nsri.res.in/pdfdoc/Advisory2023/25%20Sept-1Oct%202023.pdf) | Source-quoted soybean drying/protection reference only, conditional on an actual harvested lot. |
| `TNAU_TOMATO_POSTHARVEST_HARVESTING` | Tamil Nadu Agricultural University, tomato harvesting and post-harvest techniques | [Web page](https://agritech.tnau.ac.in/org_farm/orgfarm_tomato_harvest.html) | Source-quoted tomato maturity, grading, packing, and temperature references only; no lot or cold-chain capability is inferred. |
| `NHB_ICAP_GEO_FACILITIES` | National Horticulture Board ICAP mapped-project directory | [GIS endpoint](https://nhb.gov.in/Handlers/GeoIndiaHandlerGis.ashx) | Collection-date mapped-project candidate context only; no project type, commodity compatibility, capacity, vacancy, or booking assertion. |
| `NHB_ICAP_STATE_COMPONENTS` | National Horticulture Board ICAP state component summary | [ICAP map report](https://nhb.gov.in/IcapMap/ICAPMap_rpt.aspx) | Collection-date state aggregate context only; no district allocation, live capacity, or availability. |
| `MOFPI_COLD_CHAIN_COMPONENTS` | Ministry of Food Processing Industries, Integrated Cold Chain and Value Addition Infrastructure scheme | [Scheme page](https://mofpi.gov.in/en/Schemes/about-cold-chain) | Scheme context only; not a facility directory or availability source. |
| `WDRA_REGISTERED_WAREHOUSES_MADHYA_PRADESH`, `WDRA_REGISTERED_WAREHOUSES_MAHARASHTRA`, `WDRA_REGISTERED_WAREHOUSES_PUNJAB`, `WDRA_REGISTERED_WAREHOUSES_RAJASTHAN`, `WDRA_REGISTERED_WAREHOUSES_TAMIL_NADU` | Warehousing Development and Regulatory Authority public registered-warehouse lists | [WDRA public registry](https://wdra.gov.in/registered-wh-public) | Collection-date district registry candidate context only; registration does not prove lot acceptance, capacity, vacancy, booking, price, or transport availability. |
| `OSRM_STATIC_ROUTE_CONTEXT` | Project OSRM / OpenStreetMap contributors public route service | [Driving route endpoint](https://router.project-osrm.org/route/v1/driving) | Captured static road geometry for specified NHB coordinate pairs only; never live traffic, road closure, vehicle, freight, dispatch, or historical route availability. |

The canonical fourth-enrichment source record is
[`postharvest_source_inventory.csv`](../data/scenarios/enriched/postharvest_source_inventory.csv).
It preserves every raw path, SHA-256, provider, URL, retrieval timestamp,
temporal interpretation, and allowed-use text. Related scenario and audit
records are [`scenario_postharvest_plan_items.csv`](../data/scenarios/enriched/scenario_postharvest_plan_items.csv),
[`scenario_postharvest_rag_scope.csv`](../data/scenarios/enriched/scenario_postharvest_rag_scope.csv),
[`postharvest_site_facility_context.csv`](../data/scenarios/enriched/postharvest_site_facility_context.csv),
[`postharvest_static_route_context.csv`](../data/scenarios/enriched/postharvest_static_route_context.csv),
and [`POSTHARVEST_LOGISTICS_AUDIT.md`](../data/scenarios/enriched/POSTHARVEST_LOGISTICS_AUDIT.md).

## Final regional management and regulatory documents

Only these named documents are used by the final management bundles. They
provide regional baselines or diagnosis/threshold-triggered options, not
farm-specific prescriptions or default spray calendars. The provider, source
date, retrieval time, scope, and SHA-256 for each are frozen in
[`regional_management_source_snapshot.csv`](../data/registry/regional_management_source_snapshot.csv).

| Source ID | Provider and document | Applies to final bundle(s) | Exact official URL |
|---|---|---|---|
| `PAU_KHARIF_2026` | Punjab Agricultural University, *Package of Practices for Crops of Punjab — Kharif 2026* | Punjab rice fertilizer baseline and diagnosis-triggered crop protection | [PDF](https://www.pau.edu/content/ccil/pf/pp_kharif.pdf) |
| `PAU_RABI_2025_26` | Punjab Agricultural University, *Package of Practices for Crops of Punjab — Rabi 2025–26* | Punjab wheat fertilizer baseline and diagnosis-triggered crop protection | [PDF](https://pau.edu/content/ccil/pf/pp_rabi.pdf) |
| `ICAR_RABI_STATE_ADVISORIES_2021_22` | Indian Council of Agricultural Research, *Rabi Agro-Advisory for Farmers 2021–22* | Tamil Nadu maize and Maharashtra chickpea regional fertilizer/IPM evidence | [PDF](https://icar.org.in/sites/default/files/2022-09/Rabi-Agro-Advisory-2021-22_0.pdf) |
| `TNAU_MAIZE_FAW_2023` | Tamil Nadu Agricultural University, *Fall armyworm management in maize* | Tamil Nadu maize diagnosis-triggered fall-armyworm IPM context | [Web page](https://agritech.tnau.ac.in/crop_protection/maize/crop_prot_maize_fall_armyworm.html) |
| `ICAR_IISR_SOYBEAN_CENTRAL_ADVISORY_2024` | ICAR–Indian Institute of Soybean Research, *Weekly advisory for soybean farmers, 1–7 July 2024* | Madhya Pradesh/Rajasthan soybean regional crop-establishment and fertilizer context | [PDF](https://icar-nsri.res.in/pdfdoc/Advisory2024/July,1-7th,2024.pdf) |
| `ICAR_IISR_SOYBEAN_BULLETIN_2023` | ICAR–Indian Institute of Soybean Research, *Improved Technologies and Recommendations for Maximizing Soybean Productivity* | Madhya Pradesh/Rajasthan soybean diagnosis/ETL-triggered IPM context | [PDF](https://icar-nsri.res.in/pdfdoc/ExtensionBulletin2023E_2.pdf) |
| `TNAU_TOMATO_FERTIGATION_2014` | Tamil Nadu Agricultural University, *Tomato fertigation schedule for hybrids* | Tamil Nadu tomato hybrid drip-fertigation baseline only | [PDF](https://agritech.tnau.ac.in/horticulture/ferti_schedule.pdf) |
| `TNAU_TOMATO_EARLY_BLIGHT_2023` | Tamil Nadu Agricultural University, *Tomato early-blight integrated disease management* | Tamil Nadu tomato diagnosis-triggered early-blight context | [Web page](https://agritech.tnau.ac.in/crop_protection/tomato_diseases_2.html) |
| `CIBRC_INSECTICIDE_2026` | PPQS / CIBRC, *Major Uses of Pesticides — chemical insecticides* | Regulatory crop/problem/formulation/rate cross-checks | [PDF](https://ppqs.gov.in/sites/default/files/updated_mup_insecticide_as_on_31.03.2026_c.pdf) |
| `CIBRC_FUNGICIDE_2026` | PPQS / CIBRC, *Major Uses of Pesticides — chemical fungicides* | Regulatory crop/problem/formulation/rate cross-checks | [PDF](https://ppqs.gov.in/sites/default/files/2._chemical_mup_fungicide_as_on_31.03.2026_0.pdf) |

## Official RAG corpus sources

The combined RAG catalog remains the immutable hash/audit record, but the
complete readable source list is included in the appendix below. Every
document must still pass the per-scenario metadata gate before retrieval.

| RAG source family | Exact official source | Admitted corpus evidence |
|---|---|---|
| Initial verified action-RAG sources | The PAU, TNAU, ICAR, IISR, and PPQS/CIBRC documents in the table above, plus TNAU rice nutrient/protection and tomato fruit-borer pages named in the combined catalog | 14 hash-verified initial documents; source inventory: [`official_rag_source_inventory.csv`](../data/scenarios/enriched/official_rag_source_inventory.csv) |
| ICAR–IISR dated soybean advisories | [IISR archive index](https://icar-nsri.res.in/Advisory.html), [2021](https://icar-nsri.res.in/Advisory2021.html), [2022](https://icar-nsri.res.in/Advisory2022.html), [2023](https://icar-nsri.res.in/Advisory2023.html), [2024](https://icar-nsri.res.in/Advisory2024.html) | 27 admitted PDF documents. The catalog retains each exact PDF URL, issue week, source hash, and Central-Zone/MP/Rajasthan scope gate. |
| ICAR–CRIDA final-site documents | [ICAR–CRIDA CCP portal](https://icar-crida.res.in/CCP/) | 51 crop-profile, sowing-window, and contingency PDFs. The catalog retains every exact district PDF URL/hash and historical-context restriction. |
| Exact-week source-quoted soybean operations | Exact sources `ICAR_IISR_WEEKLY_SOYBEAN_20230925` and `ICAR_IISR_WEEKLY_SOYBEAN_20240624` in the combined catalog | 13 action/guardrail records, 57 source-scoped conditional bindings, and zero automatic farm actions; see [`EXACT_WEEK_IISR_ACTION_ENRICHMENT.md`](../data/scenarios/enriched/EXACT_WEEK_IISR_ACTION_ENRICHMENT.md). |

The expanded collector considered 120 candidates and admitted 78 additional
documents only after source-byte and scope checks. Rejected/unavailable sources
remain visible in [`expanded_official_rag_source_inventory.csv`](../data/scenarios/enriched/expanded_official_rag_source_inventory.csv) and
[`EXPANDED_OFFICIAL_SOURCE_DISCOVERY.md`](../data/scenarios/enriched/EXPANDED_OFFICIAL_SOURCE_DISCOVERY.md).

## Evaluation-only conflict fixture registry

The project also contains
[`data/conflict_fixture_registry`](../data/conflict_fixture_registry/). It is
not an external-data collection and not an agricultural enrichment. Its 60
stored counterfactual records reuse only:

- real frozen base identities from
  [`scenario_manifest.csv`](../data/scenarios/manifests/scenario_manifest.csv);
  and
- existing real source references from
  [`regional_operation_plan_items.csv`](../data/scenarios/enriched/regional_operation_plan_items.csv).

The controlled competing side is explicitly identified as
`EVALUATION_COUNTERFACTUAL_PROVENANCE_OVERLAY`, not as a new official document
or agricultural observation. It is used solely to test deterministic conflict
handling. Its own audit and source boundary are in
[`CONFLICT_FIXTURE_AUDIT.md`](../data/conflict_fixture_registry/CONFLICT_FIXTURE_AUDIT.md)
and [`DATA_SOURCES.md`](../data/conflict_fixture_registry/DATA_SOURCES.md).

The evaluation runner uses these references only after it has loaded and
checked the immutable base scenario. It then creates test-only typed claims in
memory for the real detector/coordinator policy. The overlay is not admitted
to the RAG corpus, does not appear in a normal `BenchmarkMASWorkflow` run, and
must never be cited as agricultural advice or counted as a new data source.

## Evaluation-only provenance/alignment fixture registry

[`data/provenance_fixture_registry`](../data/provenance_fixture_registry/) is
also not an external-data collection or an agricultural enrichment. It reuses
only the frozen scenario manifest and the already-cited regional operation
plan rows to create one in-memory mismatch at a time. Its six fault classes
cover plan-item crop, district, season, decision-date, and scenario-binding
identity plus the weather payload SHA-256.

Its separate `DATA_SOURCES.md` lists the exact internal artifacts and explains
which production boundary is tested. In particular, the 10 SHA-256 cases test
the shared loader verifier; they do not falsely attribute hash checking to the
provenance-summary agent. The registry cannot enter RAG, a normal batch run,
or a farmer response.

## Reproducibility and interpretation

### Phase 9 release evidence

The final v2.2 verification introduces no new agricultural source. It records
a fresh local execution environment and verifies that already-admitted
source/code artifacts still match. The official archive is
[`results/v2_2-final-reproducibility-2026-10-12`](../results/v2_2-final-reproducibility-2026-10-12/):
it contains clean-commit E0 and both-fixture verification, environment
manifests, 57/57 frozen-artifact hash checks, and refreshed E1 Ollama Metal
evidence. Earlier E0/E1 semantic reruns are recoverable historical outputs,
not v2.2 paper evidence. The Ollama model blob/digest and GPU-residency
evidence are runtime provenance, not agricultural evidence and not a citation
for any farmer-facing claim.

- The scenario manifest contains the exact NASA POWER and Agmarknet URL for
  every scenario. Its raw paths and hashes make each derived feature auditable.
- Sentinel searches preserve the POST endpoint, query hash, raw response, and
  selected quality-gated item. Pre-decision NDVI evidence is source-hashed
  representative-cell context, not crop/disease/field evidence.
- First enrichment does not rewrite frozen scenario facts. The 300-row
  `mas_enrichment_contract.csv` specifies what each agent may use or must
  abstain from claiming.
- Official RAG retrieval must filter `scenario_official_rag_scope_all.csv`
  before ranking chunks. Dated IISR advisories require exact-week matching;
  CRIDA documents remain historical district context.
- KVK and IMD GKMS were checked through their official portals but supplied no
  admitted exact crop + district + decision-date advisory. See
  [`PUBLIC_DISTRICT_KVK_ADVISORY_DISCOVERY.md`](../data/scenarios/enriched/PUBLIC_DISTRICT_KVK_ADVISORY_DISCOVERY.md).
- Do not describe WorldCover cells as farmer parcels, SoilGrids as a soil test,
  Sentinel/NDVI as disease detection, regional fertilizer guidance as a field
  dose, or PPQS/CIBRC records as a treatment order.

For the paper, cite the provider/product or dated official document above and
cite the scenario, enrichment, RAG, or action artifact that contains the exact
frozen source record used in the reported result.

## Complete admitted official RAG document list

This is the complete human-readable list of the 92 admitted RAG documents.
**Initial** sources are hash-verified regional policy/action documents.
**IISR weekly** sources are dated soybean advisories. **ICAR-CRIDA** sources
are historical final-site district context. A document may be retrieved only
within the scope, period, and restriction shown below.

| Source ID | Layer | Provider | Official document | Geography / crop scope | Source period | Use restriction |
|---|---|---|---|---|---|---|
| `PAU_KHARIF_2026` | Initial | Punjab Agricultural University | Package of Practices for Crops of Punjab — Kharif 2026 [link](<https://www.pau.edu/content/ccil/pf/pp_kharif.pdf>) | Punjab state; rice | March 2026 | Apply the existing crop, registry-geography and effective-date metadata gate before ranking. |
| `PAU_RABI_2025_26` | Initial | Punjab Agricultural University | Package of Practices for Crops of Punjab — Rabi 2025–26 [link](<https://pau.edu/content/ccil/pf/pp_rabi.pdf>) | Punjab state; wheat | August 2025 | Apply the existing crop, registry-geography and effective-date metadata gate before ranking. |
| `TNAU_RICE_NUTRIENT_2023` | Initial | Tamil Nadu Agricultural University | TNAU Agritech rice nutrient management — inorganic fertilizers [link](<https://agritech.tnau.ac.in/agriculture/agri_main_feild_%20InOrganic_biofertilizers_Rice.html>) | Tamil Nadu; includes a Cauvery delta tract distinction; rice | January 2023 | Apply the existing crop, registry-geography and effective-date metadata gate before ranking. |
| `TNAU_RICE_PROTECTION_INDEX_2023` | Initial | Tamil Nadu Agricultural University | TNAU Agritech rice crop-protection index [link](<https://agritech.tnau.ac.in/agriculture/crop_prot_rice%20crop.html>) | Tamil Nadu; rice | January 2023 | Apply the existing crop, registry-geography and effective-date metadata gate before ranking. |
| `TNAU_TOMATO_FERTIGATION_2014` | Initial | Tamil Nadu Agricultural University | TNAU tomato fertigation schedule for hybrids [link](<https://agritech.tnau.ac.in/horticulture/ferti_schedule.pdf>) | Tamil Nadu; hybrid tomato under the documented drip-fertigation system; tomato | 29.10.2014 | Apply the existing crop, registry-geography and effective-date metadata gate before ranking. |
| `TNAU_TOMATO_FRUIT_BORER_2023` | Initial | Tamil Nadu Agricultural University | TNAU Agritech tomato fruit-borer integrated management [link](<https://agritech.tnau.ac.in/crop_protection/tomato/tomato_1.html>) | Tamil Nadu; tomato | June 2023 | Apply the existing crop, registry-geography and effective-date metadata gate before ranking. |
| `TNAU_TOMATO_EARLY_BLIGHT_2023` | Initial | Tamil Nadu Agricultural University | TNAU Agritech tomato early-blight integrated disease management [link](<https://agritech.tnau.ac.in/crop_protection/tomato_diseases_2.html>) | Tamil Nadu; tomato | June 2023 | Apply the existing crop, registry-geography and effective-date metadata gate before ranking. |
| `TNAU_MAIZE_FAW_2023` | Initial | Tamil Nadu Agricultural University | TNAU fall-armyworm management in maize [link](<https://agritech.tnau.ac.in/crop_protection/maize/crop_prot_maize_fall_armyworm.html>) | Tamil Nadu; maize | May 2023 | Apply the existing crop, registry-geography and effective-date metadata gate before ranking. |
| `ICAR_IISR_SOYBEAN_BULLETIN_2023` | Initial | ICAR–Indian Institute of Soybean Research | Improved Technologies and Recommendations for Maximizing Soybean Productivity [link](<https://icar-nsri.res.in/pdfdoc/ExtensionBulletin2023E_2.pdf>) | AICRP soybean Central Zone: Madhya Pradesh, Bundelkhand Uttar Pradesh, Rajasthan, Gujarat and north-west Maharashtra; soybean | 2023 | Apply the existing crop, registry-geography and effective-date metadata gate before ranking. |
| `ICAR_IISR_SOYBEAN_CENTRAL_ADVISORY_2024` | Initial | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly advisory for soybean farmers, 1–7 July 2024 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2024/July,1-7th,2024.pdf>) | Central soybean zone; applied only to registered Madhya Pradesh and Rajasthan sites; soybean | 01.07.2024 | Apply the existing crop, registry-geography and effective-date metadata gate before ranking. |
| `ICAR_KHARIF_STATE_ADVISORIES_2025` | Initial | Indian Council of Agricultural Research | ICAR Kharif Agro-Advisories for Farmers 2025 [link](<https://icar.org.in/sites/default/files/Circulars/ICAR-En-Kharif-Agro-Advisories-for-Farmers-2025.pdf>) | State-specific chapters; this registry uses only the Haryana & Delhi, Karnataka, Maharashtra and Rajasthan chapters for compatible kharif sites; rice;maize;soybean;other kharif crops | May 2025 | Apply the existing crop, registry-geography and effective-date metadata gate before ranking. |
| `ICAR_RABI_STATE_ADVISORIES_2021_22` | Initial | Indian Council of Agricultural Research | ICAR Rabi Agro-Advisory for Farmers 2021–22 [link](<https://icar.org.in/sites/default/files/2022-09/Rabi-Agro-Advisory-2021-22_0.pdf>) | State-specific chapters; this registry uses only the Haryana & Delhi, Uttar Pradesh, Madhya Pradesh, Maharashtra, Karnataka and Tamil Nadu & Puducherry chapters for compatible rabi sites; wheat;chickpea;maize;tomato;other rabi crops | September 2021 | Apply the existing crop, registry-geography and effective-date metadata gate before ranking. |
| `CIBRC_INSECTICIDE_2026` | Initial | PPQS / Central Insecticides Board and Registration Committee | CIBRC Major Uses of Pesticides — chemical insecticides [link](<https://ppqs.gov.in/sites/default/files/updated_mup_insecticide_as_on_31.03.2026_c.pdf>) | India national regulatory record; registered crops | 31.03.2026 | Registration/label context only; never a treatment recommendation. |
| `CIBRC_FUNGICIDE_2026` | Initial | PPQS / Central Insecticides Board and Registration Committee | CIBRC Major Uses of Pesticides — chemical fungicides [link](<https://ppqs.gov.in/sites/default/files/2._chemical_mup_fungicide_as_on_31.03.2026_0.pdf>) | India national regulatory record; registered crops | 31.03.2026 | Registration/label context only; never a treatment recommendation. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20210906` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 06-12 Sept 2021 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2021/6-12September2021.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2021-09-06 to 2021-09-12 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20210809` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 9-15 Aug 2021 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2021/9-15August2021.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2021-08-09 to 2021-08-15 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20210816` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 16-22 Aug 2021 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2021/16-22August2021.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2021-08-16 to 2021-08-22 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20210823` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 23-29 Aug 2021 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2021/23-29August2021.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2021-08-23 to 2021-08-29 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20210830` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 30 Aug- 5 Sept 2021 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2021/30August-5Sept2021.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2021-08-30 to 2021-09-05 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20210712` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 12-18 July 2021 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2021/12-18July2021.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2021-07-12 to 2021-07-18 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20220808` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 08-14 August 2022 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2022/08_14Aug2022.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2022-08-08 to 2022-08-14 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20220822` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 22-28 August 2022 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2022/22_28Aug2022.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2022-08-22 to 2022-08-28 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20220829` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 29 August- 04 September 2022 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2022/29Aug_4Sept2022.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2022-08-29 to 2022-09-04 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20220905` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 05-11 September 2022 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2022/05_11Sept2022.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2022-09-05 to 2022-09-11 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20230710` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 10-16 July 2023 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2023/10-16july2023.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2023-07-10 to 2023-07-16 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20230717` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 17-23 July 2023 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2023/17-23july2023.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2023-07-17 to 2023-07-23 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20230724` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 24-30July 2023 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2023/24-30July2023.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2023-07-24 to 2023-07-30 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20230814` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 14-20 August 2023 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2023/14-20Aug2023.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2023-08-14 to 2023-08-20 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20230821` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 21-27 August 2023 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2023/21-27Aug2023.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2023-08-21 to 2023-08-27 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20230904` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 04-10 September 2023 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2023/4-10Sept,%202023.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2023-09-04 to 2023-09-10 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20230918` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 18-24 September 2023 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2023/18-24%20Sept,2023.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2023-09-18 to 2023-09-24 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20230925` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 25Sep-01Oct 2023 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2023/25%20Sept-1Oct%202023.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2023-09-25 to 2023-10-01 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20240610` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 10-16 June 2024 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2024/June%2010-16,%202024.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2024-06-10 to 2024-06-16 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20240617` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 17-23 June 2024 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2024/June%2017-23,%202024.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2024-06-17 to 2024-06-23 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20240624` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 24-30 June 2024 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2024/June%2024-30,%20%202024.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2024-06-24 to 2024-06-30 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20240701` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 01-07 July 2024 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2024/July,1-7,2024.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2024-07-01 to 2024-07-07 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20240708` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 08-14 July 2024 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2024/July,8-14,%202024.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2024-07-08 to 2024-07-14 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20240722` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 22-28 July 2024 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2024/July,22-28,2024.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2024-07-22 to 2024-07-28 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20240729` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 29 July-04 August 2024 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2024/July,29-%204,August,2024.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2024-07-29 to 2024-08-04 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20240805` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 05-11 August 2024 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2024/Aug,5-11,2024.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2024-08-05 to 2024-08-11 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_IISR_WEEKLY_SOYBEAN_20240819` | IISR weekly | ICAR–Indian Institute of Soybean Research | ICAR-IISR weekly soybean advisory, 19-25 August 2024 [link](<https://icar-nsri.res.in/pdfdoc/Advisory2024/Aug,19-25,2024.pdf>) | Central soybean zone; Madhya Pradesh and Rajasthan only; soybean | 2024-08-19 to 2024-08-25 | Exact issue week, crop and Central-Zone state must pass before ranking. |
| `ICAR_CRIDA_MP_DEWAS_CONTINGENCY` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district weather contingency document — Dewas, Madhya Pradesh [link](<https://icar-crida.res.in/CCP/MP/Dewas/3.11.pdf>) | Dewas, Madhya Pradesh district; soybean | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_MP_INDORE_CONTINGENCY` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district weather contingency document — Indore, Madhya Pradesh [link](<https://icar-crida.res.in/CCP/MP/Indore/3.11.pdf>) | Indore, Madhya Pradesh district; soybean | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_MP_UJJAIN_CONTINGENCY` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district weather contingency document — Ujjain, Madhya Pradesh [link](<https://icar-crida.res.in/CCP/MP/Ujjain/3.11.pdf>) | Ujjain, Madhya Pradesh district; soybean | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_PB_BATHINDA_CONTINGENCY` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district weather contingency document — Bathinda, Punjab [link](<https://icar-crida.res.in/CCP/PB/Bathinda/3.11.pdf>) | Bathinda, Punjab district; rice;wheat | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_PB_LUDHIANA_CONTINGENCY` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district weather contingency document — Ludhiana, Punjab [link](<https://icar-crida.res.in/CCP/PB/Ludhiana/3.11.pdf>) | Ludhiana, Punjab district; rice | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_PB_MANSA_CONTINGENCY` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district weather contingency document — Mansa, Punjab [link](<https://icar-crida.res.in/CCP/PB/Mansa/3.11.pdf>) | Mansa, Punjab district; rice;wheat | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_PB_PATIALA_CONTINGENCY` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district weather contingency document — Patiala, Punjab [link](<https://icar-crida.res.in/CCP/PB/Patiala/3.11.pdf>) | Patiala, Punjab district; rice;wheat | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_PB_SANGRUR_CONTINGENCY` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district weather contingency document — Sangrur, Punjab [link](<https://icar-crida.res.in/CCP/PB/Sangrur/3.11.pdf>) | Sangrur, Punjab district; rice;wheat | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_TN_NAMAKKAL_CONTINGENCY` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district weather contingency document — Namakkal, Tamil Nadu [link](<https://icar-crida.res.in/CCP/TN/Namakkal/3.11.pdf>) | Namakkal, Tamil Nadu district; maize | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_MH_BEED_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Beed, Maharashtra [link](<https://icar-crida.res.in/CCP/MH/Beed/1.7.pdf>) | Beed, Maharashtra district; chickpea | 2011-12;2012-13;2014-15 | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_MH_JALNA_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Jalna, Maharashtra [link](<https://icar-crida.res.in/CCP/MH/Jalna/1.7.pdf>) | Jalna, Maharashtra district; chickpea | 2009-10;2013-14;2014-15 | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_MH_LATUR_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Latur, Maharashtra [link](<https://icar-crida.res.in/CCP/MH/Latur/1.7.pdf>) | Latur, Maharashtra district; chickpea | 1990-91;2010-11;2011-12;2012-13;2013-14;2014-15 | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_MH_NANDED_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Nanded, Maharashtra [link](<https://icar-crida.res.in/CCP/MH/Nanded/1.7.pdf>) | Nanded, Maharashtra district; chickpea | 2007-08;2008-09;2014-15;2016-17 | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_MH_PARBHANI_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Parbhani, Maharashtra [link](<https://icar-crida.res.in/CCP/MH/Parbhani/1.7.pdf>) | Parbhani, Maharashtra district; chickpea | 2008-09 | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_MP_DEWAS_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Dewas, Madhya Pradesh [link](<https://icar-crida.res.in/CCP/MP/Dewas/1.7.pdf>) | Dewas, Madhya Pradesh district; soybean | 2008-09 | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_MP_INDORE_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Indore, Madhya Pradesh [link](<https://icar-crida.res.in/CCP/MP/Indore/1.7.pdf>) | Indore, Madhya Pradesh district; soybean | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_MP_UJJAIN_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Ujjain, Madhya Pradesh [link](<https://icar-crida.res.in/CCP/MP/Ujjain/1.7.pdf>) | Ujjain, Madhya Pradesh district; soybean | 2008-09 | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_PB_BATHINDA_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Bathinda, Punjab [link](<https://icar-crida.res.in/CCP/PB/Bathinda/1.7.pdf>) | Bathinda, Punjab district; rice;wheat | 2007-08;2008-09 | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_PB_LUDHIANA_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Ludhiana, Punjab [link](<https://icar-crida.res.in/CCP/PB/Ludhiana/1.7.pdf>) | Ludhiana, Punjab district; rice;wheat | 2008-09 | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_PB_MANSA_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Mansa, Punjab [link](<https://icar-crida.res.in/CCP/PB/Mansa/1.7.pdf>) | Mansa, Punjab district; rice;wheat | 2007-08 | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_PB_PATIALA_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Patiala, Punjab [link](<https://icar-crida.res.in/CCP/PB/Patiala/1.7.pdf>) | Patiala, Punjab district; rice;wheat | 2008-09 | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_PB_SANGRUR_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Sangrur, Punjab [link](<https://icar-crida.res.in/CCP/PB/Sangrur/1.7.pdf>) | Sangrur, Punjab district; rice;wheat | 2008-09 | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_RJ_BARAN_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Baran, Rajasthan [link](<https://icar-crida.res.in/CCP/RJ/Baran/1.7.pdf>) | Baran, Rajasthan district; soybean | 2008-09 | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_RJ_JHALAWAR_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Jhalawar, Rajasthan [link](<https://icar-crida.res.in/CCP/RJ/Jhalawar/1.7.pdf>) | Jhalawar, Rajasthan district; soybean | 2008-09 | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_TN_ARIYALUR_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Ariyalur, Tamil Nadu [link](<https://icar-crida.res.in/CCP/TN/Ariyalur/1.7.pdf>) | Ariyalur, Tamil Nadu district; maize | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_TN_COIMBATORE_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Coimbatore, Tamil Nadu [link](<https://icar-crida.res.in/CCP/TN/Coimbatore/1.7.pdf>) | Coimbatore, Tamil Nadu district; maize;tomato | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_TN_DHARMAPURI_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Dharmapuri, Tamil Nadu [link](<https://icar-crida.res.in/CCP/TN/Dharmapuri/1.7.pdf>) | Dharmapuri, Tamil Nadu district; tomato | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_TN_ERODE_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Erode, Tamil Nadu [link](<https://icar-crida.res.in/CCP/TN/Erode/1.7.pdf>) | Erode, Tamil Nadu district; maize | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_TN_KRISHNAGIRI_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Krishnagiri, Tamil Nadu [link](<https://icar-crida.res.in/CCP/TN/Krishnagiri/1.7.pdf>) | Krishnagiri, Tamil Nadu district; tomato | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_TN_NAMAKKAL_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Namakkal, Tamil Nadu [link](<https://icar-crida.res.in/CCP/TN/Namakkal/1.7.pdf>) | Namakkal, Tamil Nadu district; maize | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_TN_SALEM_CROP_PROFILE` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district crop profile document — Salem, Tamil Nadu [link](<https://icar-crida.res.in/CCP/TN/Salem/1.7.pdf>) | Salem, Tamil Nadu district; maize;tomato | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_MH_BEED_SOWING_WINDOW` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district sowing window document — Beed, Maharashtra [link](<https://icar-crida.res.in/CCP/MH/Beed/1.12.pdf>) | Beed, Maharashtra district; chickpea | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_MH_JALNA_SOWING_WINDOW` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district sowing window document — Jalna, Maharashtra [link](<https://icar-crida.res.in/CCP/MH/Jalna/1.12.pdf>) | Jalna, Maharashtra district; chickpea | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_MH_LATUR_SOWING_WINDOW` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district sowing window document — Latur, Maharashtra [link](<https://icar-crida.res.in/CCP/MH/Latur/1.12.pdf>) | Latur, Maharashtra district; chickpea | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_MH_NANDED_SOWING_WINDOW` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district sowing window document — Nanded, Maharashtra [link](<https://icar-crida.res.in/CCP/MH/Nanded/1.12.pdf>) | Nanded, Maharashtra district; chickpea | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_MH_PARBHANI_SOWING_WINDOW` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district sowing window document — Parbhani, Maharashtra [link](<https://icar-crida.res.in/CCP/MH/Parbhani/1.12.pdf>) | Parbhani, Maharashtra district; chickpea | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_MP_DEWAS_SOWING_WINDOW` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district sowing window document — Dewas, Madhya Pradesh [link](<https://icar-crida.res.in/CCP/MP/Dewas/1.12.pdf>) | Dewas, Madhya Pradesh district; soybean | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_MP_INDORE_SOWING_WINDOW` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district sowing window document — Indore, Madhya Pradesh [link](<https://icar-crida.res.in/CCP/MP/Indore/1.12.pdf>) | Indore, Madhya Pradesh district; soybean | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_MP_UJJAIN_SOWING_WINDOW` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district sowing window document — Ujjain, Madhya Pradesh [link](<https://icar-crida.res.in/CCP/MP/Ujjain/1.12.pdf>) | Ujjain, Madhya Pradesh district; soybean | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_PB_BATHINDA_SOWING_WINDOW` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district sowing window document — Bathinda, Punjab [link](<https://icar-crida.res.in/CCP/PB/Bathinda/1.12.pdf>) | Bathinda, Punjab district; rice;wheat | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_PB_LUDHIANA_SOWING_WINDOW` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district sowing window document — Ludhiana, Punjab [link](<https://icar-crida.res.in/CCP/PB/Ludhiana/1.12.pdf>) | Ludhiana, Punjab district; rice;wheat | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_PB_MANSA_SOWING_WINDOW` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district sowing window document — Mansa, Punjab [link](<https://icar-crida.res.in/CCP/PB/Mansa/1.12.pdf>) | Mansa, Punjab district; rice;wheat | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_PB_PATIALA_SOWING_WINDOW` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district sowing window document — Patiala, Punjab [link](<https://icar-crida.res.in/CCP/PB/Patiala/1.12.pdf>) | Patiala, Punjab district; rice;wheat | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_PB_SANGRUR_SOWING_WINDOW` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district sowing window document — Sangrur, Punjab [link](<https://icar-crida.res.in/CCP/PB/Sangrur/1.12.pdf>) | Sangrur, Punjab district; rice;wheat | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_RJ_BARAN_SOWING_WINDOW` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district sowing window document — Baran, Rajasthan [link](<https://icar-crida.res.in/CCP/RJ/Baran/1.12.pdf>) | Baran, Rajasthan district; soybean | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_RJ_JHALAWAR_SOWING_WINDOW` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district sowing window document — Jhalawar, Rajasthan [link](<https://icar-crida.res.in/CCP/RJ/Jhalawar/1.12.pdf>) | Jhalawar, Rajasthan district; soybean | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_TN_ARIYALUR_SOWING_WINDOW` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district sowing window document — Ariyalur, Tamil Nadu [link](<https://icar-crida.res.in/CCP/TN/Ariyalur/1.12.pdf>) | Ariyalur, Tamil Nadu district; maize | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_TN_COIMBATORE_SOWING_WINDOW` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district sowing window document — Coimbatore, Tamil Nadu [link](<https://icar-crida.res.in/CCP/TN/Coimbatore/1.12.pdf>) | Coimbatore, Tamil Nadu district; maize | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_TN_ERODE_SOWING_WINDOW` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district sowing window document — Erode, Tamil Nadu [link](<https://icar-crida.res.in/CCP/TN/Erode/1.12.pdf>) | Erode, Tamil Nadu district; maize | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_TN_NAMAKKAL_SOWING_WINDOW` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district sowing window document — Namakkal, Tamil Nadu [link](<https://icar-crida.res.in/CCP/TN/Namakkal/1.12.pdf>) | Namakkal, Tamil Nadu district; maize | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
| `ICAR_CRIDA_TN_SALEM_SOWING_WINDOW` | ICAR-CRIDA | ICAR–Central Research Institute for Dryland Agriculture | ICAR-CRIDA district sowing window document — Salem, Tamil Nadu [link](<https://icar-crida.res.in/CCP/TN/Salem/1.12.pdf>) | Salem, Tamil Nadu district; maize | historical_date_not_extracted | Historical district context only; never current advice or a direct farm operation. |
