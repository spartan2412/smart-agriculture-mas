# Enrichment Data Sources

This layer adds derived context without changing the frozen scenario records.
Each row carries its source URL, raw-response path, and appropriate SHA-256
hash; [ENRICHMENT_AUDIT.md](ENRICHMENT_AUDIT.md) validates those links.

| Evidence | Public source | Exact use in this layer | Not used to claim |
| --- | --- | --- | --- |
| Historical weather and water context | [NASA POWER Daily API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) | Exact scenario date-window daily AG parameters: temperature, precipitation, humidity, wind, radiation, modelled top/root-zone wetness, and land evaporation | Tomorrow's forecast, field moisture, or irrigation dose |
| Sentinel scene metadata and representative-cell NDVI | [Microsoft Planetary Computer Sentinel-2 L2A STAC](https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a) | The exact frozen Sentinel-2 item ID; signed B04, B08, and SCL point reads only after item/quality validation | A crop-labelled field, crop stage, parcel average, or disease diagnosis |
| Sentinel recovery context | [Microsoft Planetary Computer Sentinel-2 L2A STAC](https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a) | Only a quality-gated candidate already in the original frozen same-month STAC response, selected before NDVI calculation by cloud, nodata, timestamp, coordinate containment, and clear SCL | A replacement for the frozen item, or a crop/field label |
| Historical market context | [Agmarknet monthly wholesale-price API](https://api.agmarknet.gov.in/v1/price-trend/wholesale-prices-monthly) | Current, prior-month, and same-calendar-month-prior-year price columns published in the exact frozen official report | A price forecast or sell/hold instruction |
| Static soil context | [ISRIC SoilGrids](https://www.isric.org/explore/soilgrids) | Existing frozen pH, texture, organic-carbon, and nitrogen predictors are carried into the MAS contract | Field moisture, available N/P/K, or a farm-specific fertilizer dose |
| Regional fertilizer and IPM policy | [ICAR-National Soil Research Institute](https://icar-nsri.res.in/) and [CIBRC/PPQS](https://ppqs.gov.in/divisions/central-insecticide-board-registration-committee) | Existing final management bundles and PPQS validation, linked per scenario in `management_policy_features.csv` | A diagnosis-triggered treatment or a personalized prescription |
| Initial official action-RAG documents | [Punjab Agricultural University](https://www.pau.edu/), [Tamil Nadu Agricultural University Agritech Portal](https://agritech.tnau.ac.in/), [ICAR](https://icar.org.in/), [ICAR–Indian Institute of Soybean Research](https://icar-nsri.res.in/), and [CIBRC/PPQS](https://ppqs.gov.in/divisions/central-insecticide-board-registration-committee) | Only documents pre-enumerated in `data/registry/regional_management_source_snapshot.csv`, whose downloaded raw bytes exactly reproduce the registry SHA-256; page/section extraction, verbatim operation records, and pre-retrieval RAG metadata filtering | A source outside its crop, registry geography, or effective date; a CIBRC registration record as a treatment recommendation |
| Dated soybean advisory archive | [ICAR–Indian Institute of Soybean Research advisory archive](https://icar-nsri.res.in/Advisory.html) and its [2021](https://icar-nsri.res.in/Advisory2021.html), [2022](https://icar-nsri.res.in/Advisory2022.html), [2023](https://icar-nsri.res.in/Advisory2023.html), and [2024](https://icar-nsri.res.in/Advisory2024.html) pages | Hash-frozen weekly soybean PDFs whose extracted text verifies crop and Central-Zone/Madhya Pradesh/Rajasthan scope; exact weekly issue date is a mandatory gate | An archived PDF with unverified zone scope, an ambiguous archive date, or a recommendation outside its exact week |
| District historical crop context | [ICAR–CRIDA Crop Contingency Plans](https://icar-crida.res.in/CCP/) | Crop-profile, sowing-window, and contingency PDFs already SHA-256 verified for the final registered district sites; exact district/crop background retrieval only | A current advisory, current weather decision, farm-specific irrigation/fertilizer/spray instruction, or unsupported crop/district match |
| Exact-week soybean operations | [ICAR–IISR 2023 advisory archive](https://icar-nsri.res.in/Advisory2023.html) and [2024 advisory archive](https://icar-nsri.res.in/Advisory2024.html) | Visually reviewed, page-quoted operations only from 25 September-1 October 2023 and 24-30 June 2024 PDFs when their exact issue week, crop, and Central-Zone state match | An automatic farm operation when crop stage, field condition, forecast, soil test, diagnosis, or farming-system evidence is absent |
| Recovered Punjab-rice operations | [PAU Kharif package original URL](https://www.pau.edu/content/ccil/pf/pp_kharif.pdf), preserved at [2023](https://web.archive.org/web/20230918105856id_/https://www.pau.edu/content/ccil/pf/pp_kharif.pdf), [2024](https://web.archive.org/web/20240830235813id_/https://www.pau.edu/content/ccil/pf/pp_kharif.pdf), and [2025](https://web.archive.org/web/20250626143125id_/https://www.pau.edu/content/ccil/pf/pp_kharif.pdf) | Page-11 quotations from a source self-identifying as its named Kharif year; both official and preservation URLs, capture time, raw/extracted hashes, and capture-derived time gates are retained | Treating the archive as a new publisher, using an annual package outside its conservative time window, or omitting the crop-maturity gate |
| Recovered Punjab-wheat operations | [PAU Rabi package original URL](https://pau.edu/content/ccil/pf/pp_rabi.pdf), preserved at [2021–22](https://web.archive.org/web/20220108015141id_/https://www.pau.edu/content/ccil/pf/pp_rabi.pdf), [2023–24](https://web.archive.org/web/20230918105852id_/https://www.pau.edu/content/ccil/pf/pp_rabi.pdf) and [2024–25](https://web.archive.org/web/20250523045635id_/https://pau.edu/content/ccil/pf/pp_rabi.pdf) | Page-quoted wheat harvest operations from PDFs self-identifying as their named Rabi year; original/replay URLs, archive capture, preserved original-server Last-Modified, raw/extracted hashes and time gates are retained | Treating archive replay time as the original publication date, applying a Rabi package outside its derived annual window, or omitting maturity gating |
| Maharashtra chickpea technical operation | [MPKV Rahuri Extension Publications](https://mpkv.ac.in/Extension/ExtensionPublication) and [*Krishi Darshani 2023* PDF](https://mpkv.ac.in/Uploads/Publication/Krishi%20Darshani%20%202023_20230607043125.pdf) | Hash-frozen official Maharashtra extension guide, its official listing, and original-server `Last-Modified` (`2023-06-07T11:01:25Z`), plus hash-linked page rasters and a limited visual transcription of the statewide-scope and chickpea hard-pod harvest passages because the legacy Marathi font cannot be reliably Unicode-extracted | Treating the state technical guide as a weekly or district advisory, extending it before 7 June 2023, inferring hard-pod maturity or crop dryness, or issuing a direct farm action |
| Regional operation-plan projection | Existing ICAR–CRIDA crop-season evidence, verified regional management sources, and the source-quoted official action catalog listed above | A source-linked calendar, nutrient-policy, IPM-policy, and conditional-operation planning structure for each frozen scenario | Reclassifying a policy reference as a historical advisory, inferring field conditions, or issuing a direct farm action |
| Public district/KVK advisory availability | [ICAR KVK portal](https://kvk.icar.gov.in/) and [IMD GKMS](https://agromet.imd.gov.in/) | Reproducible anonymous access and scope check recorded in `public_district_kvk_advisory_discovery.csv` | A district advisory when the official source is inaccessible, login-gated, state/zone-scoped, static, undated, or otherwise fails crop + district + issue-date gates |
| Historical district-advisory access | [IMD GKMS Agro Advisory](https://agromet.imd.gov.in/) | Anonymous access probe, raw response, redirect/access status, and binding of available official ICAR/IISR sources at their stated zone/state scope | An invented district advisory; a state or zone document labelled as district-specific |
| Pre-decision NDVI chronology | [Microsoft Planetary Computer Sentinel-2 L2A STAC](https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a) | Reused source-hashed endpoint context plus quality-gated older scenes in a 90-day pre-decision window; STAC raw payloads, SCL attempts, B04/B08 observations, and numerical trends | Crop condition, parcel identity, crop stage, disease, field moisture, or an action trigger |
| Fourth enrichment: crop-scoped post-harvest handling | [PAU](https://www.pau.edu/), [ICAR](https://icar.org.in/), [ICAR–IISR](https://icar-nsri.res.in/), [MPKV](https://mpkv.ac.in/), and [TNAU](https://agritech.tnau.ac.in/) | Fourteen source-quoted crop-handling operations and exact-crop RAG passages, bound to the six benchmark crops and preserved with source locators and hashes | Harvest readiness, lot moisture, a direct farm action, or cross-crop retrieval |
| Fourth enrichment: infrastructure context | [NHB ICAP](https://nhb.gov.in/IcapMap/ICAPMap_rpt.aspx), [MoFPI cold-chain scheme](https://mofpi.gov.in/en/Schemes/about-cold-chain), [WDRA public registry](https://wdra.gov.in/registered-wh-public), and [OSRM public routing](https://router.project-osrm.org/route/v1/driving) | Collection-date public facility/warehouse/state-infrastructure records and static road geometry, retained as source-linked contextual records | Commodity acceptance, capacity, vacancy, booking, dispatch, freight, vehicle availability, live traffic, storage duration, or a sell/hold recommendation |

The primary market builder deliberately uses the frozen official reports rather
than a new bulk query. The extended-lookback experiment is documented in
[README.md](README.md) but is not part of the MAS input contract because the
public endpoint rate-limited batch retrieval.

The recovery feasibility and its exact scope are documented in
[RECOVERY_FEASIBILITY.md](RECOVERY_FEASIBILITY.md).

The combined official-source inventory and exact per-document official URLs are
in `official_rag_corpus_catalog.csv`; every chunk retains the same
`official_url` and source SHA-256 in `official_rag_corpus_all_chunks.csv`. The
mandatory combined metadata decision is in `scenario_official_rag_scope_all.csv`.
The underlying initial and expanded layer files remain present for source-level
audit and reproducibility. Sources considered but excluded, including the
tested unavailable historical PAU paths and anonymous IMD GKMS access barrier,
are documented in
[EXPANDED_OFFICIAL_SOURCE_DISCOVERY.md](EXPANDED_OFFICIAL_SOURCE_DISCOVERY.md).

## Fourth-enrichment source contract

The fourth enrichment is implemented and loaded by the benchmark path. Its
canonical record is [postharvest_source_inventory.csv](postharvest_source_inventory.csv),
which retains every provider, official URL, raw snapshot path, SHA-256, source
locator, retrieval time, temporal interpretation, and allowed-use rule. The
related records are:

- [postharvest_operation_library.csv](postharvest_operation_library.csv) —
  source-quoted technical handling operations and their missing lot condition;
- [scenario_postharvest_plan_items.csv](scenario_postharvest_plan_items.csv) —
  700 crop-scoped conditional plan items for 300 frozen scenarios;
- [scenario_postharvest_rag_scope.csv](scenario_postharvest_rag_scope.csv) —
  exact-crop retrieval allow-list; and
- [POSTHARVEST_LOGISTICS_AUDIT.md](POSTHARVEST_LOGISTICS_AUDIT.md) — eight
  passed integrity, profile, binding, infrastructure, route, and scope checks.

See [POSTHARVEST_LOGISTICS_ENRICHMENT.md](POSTHARVEST_LOGISTICS_ENRICHMENT.md)
for the complete data contract. The project-wide reference list, including
each individual public source and its permitted use, is
[Documentation/DATA_SOURCES.md](../../../Documentation/DATA_SOURCES.md).
