# Fourth Enrichment: Post-Harvest Storage and Logistics Context

## Purpose

This fourth enrichment adds a source-audited post-harvest layer to the frozen 300-scenario benchmark. It is consumed by the implemented deterministic **Post-Harvest Storage and Logistics Agent** and by the crop-scoped post-harvest RAG path.

It answers a narrower, defensible question:

> Given this crop and verified study region, what official handling practices and public infrastructure records may be presented as a conditional post-harvest plan?

It does **not** claim that a historic scenario contains a real harvested lot, lot moisture, tomato ripeness, grade, warehouse vacancy, commodity acceptance, road travel time, truck availability, freight quote, booking, dispatch, or sale decision.

## Evidence boundary

Two source clocks are intentionally separated.

| Layer | What it represents | Permitted use | Never infer |
| --- | --- | --- | --- |
| Crop-handling operation | Source-quoted technical handling guidance | Conditional operation in a crop-specific plan | A lot is ready, dry, mature, sound, or meets any stated threshold |
| NHB ICAP project map and component totals | Public infrastructure records captured at enrichment collection time | Named regional infrastructure context and static geodesic proximity context | Facility type/service fit, temperature capability, vacancy, booking, or historical availability |
| WDRA public warehouse registry | Public registration metadata captured at enrichment collection time | Named, district-matched registry candidate for dry commodities | Commodity acceptance, occupancy, lot acceptance, capacity available to the farmer, booking, or price |
| Static OSRM route context | Collection-date road geometry between a tomato site and a mapped NHB project | Static road-distance/duration context only | Live traffic, road closure, vehicle availability, freight, service fit, booking, dispatch, or historical access |
| Post-harvest RAG scope | Exact crop-filtered quoted passages | Retrieve only for the matching crop and preserve condition/source | Cross-crop retrieval or a farm-specific action |

The system must retain this distinction when integrating the enrichment. In particular, a WDRA `Active` record means the public registry displayed that status at collection time; it is not proof of usable capacity now or on a scenario's historic decision date.

## Coverage

| Artifact | Count | Coverage |
| --- | ---: | --- |
| Crop handling profiles | 6 | Rice, wheat, maize, chickpea, soybean, tomato |
| Source-quoted handling operations | 14 | 1–4 operations per crop, all conditional |
| NHB mapped project records | 1,207 | Benchmark states only |
| WDRA registered warehouse records | 5,701 | Madhya Pradesh, Maharashtra, Punjab, Rajasthan, Tamil Nadu |
| NHB state component summaries | 23 | All five benchmark states |
| Site-level infrastructure candidates | 90 | Up to three public candidates for each of 30 frozen sites |
| Static tomato-to-project road-geometry records | 15 | Three candidate links for each of five tomato sites |
| Scenario-level post-harvest plan items | 700 | All 300 frozen scenarios |
| Crop-filtered RAG passages/scopes | 14 / 700 | Exact crop scope only |

Each of the 30 sites has three source-linked candidate records in the public collection-date directory:

- tomato sites use nearest same-state NHB mapped project records, with a clearly labelled **geodesic** distance only;
- rice, wheat, maize, chickpea, and soybean sites use up to three WDRA records whose registry district exactly matches the frozen study district.

For the tomato/NHB links, a separate collection-date OSRM artifact also records static road distance and duration. It is **not** traffic-aware and is not used for dispatch, freight, availability, or service-suitability claims.

This is an infrastructure directory, not a recommendation engine. Candidate ranking is for transparent context display only.

## Handling profile content

| Crop | Source-quoted plan content | Required but unobserved condition |
| --- | --- | --- |
| Rice | Proper maturity/avoid night harvest; drying and storage moisture context | Variety-specific maturity; harvested-lot moisture and condition |
| Wheat | Fully-ripe harvest/thresh; dry before storage if moisture exceeds the stated threshold | Full maturity; lot-specific moisture |
| Maize | Dried brown husk/15–20% shelling context; dry ears after harvest | Husk state; lot moisture; harvest status |
| Chickpea | Harvest/thresh only after hard pods and when crop is not wet | Pod hardness; crop dryness |
| Soybean | 90% yellow-pod harvest context; quoted threshing speed; sun-dry/protect from rain | Pod maturity; harvest status; thresher configuration; lot condition |
| Tomato | Market-dependent maturity; remove unsound fruit; protective packing; temperature/humidity context | Fruit maturity; lot grade; destination; verified cold-chain capability |

The exact quotations, source locations, source hashes, and safety conditions are stored in [postharvest_operation_library.csv](postharvest_operation_library.csv). Farmer-facing text may be concise, but the citation and condition must remain available in the technical trace.

## Public sources captured

All source URLs, raw snapshots, SHA-256 hashes, retrieval timestamps, and allowed-use statements are in [postharvest_source_inventory.csv](postharvest_source_inventory.csv).

Crop handling sources:

- Punjab Agricultural University — [Kharif Package of Practices](https://www.pau.edu/content/ccil/pf/pp_kharif.pdf) (rice).
- Punjab Agricultural University — [Rabi Package of Practices](https://pau.edu/content/ccil/pf/pp_rabi.pdf) (wheat).
- Indian Council of Agricultural Research — [Rabi Agro-Advisory for Farmers 2021–22](https://icar.org.in/sites/default/files/2022-09/Rabi-Agro-Advisory-2021-22_0.pdf) (maize technical reference).
- Mahatma Phule Krishi Vidyapeeth — [Krishi Darshani 2023](https://mpkv.ac.in/Uploads/Publication/Krishi%20Darshani%20%202023_20230607043125.pdf) (chickpea).
- ICAR–Indian Institute of Soybean Research — [Improved Technologies and Recommendations for Maximizing Soybean Productivity](https://icar-nsri.res.in/pdfdoc/ExtensionBulletin2023E_2.pdf) and [weekly advisory, 25 Sep–01 Oct 2023](https://icar-nsri.res.in/pdfdoc/Advisory2023/25%20Sept-1Oct%202023.pdf) (soybean).
- Tamil Nadu Agricultural University — [Tomato harvesting and post-harvest techniques](https://agritech.tnau.ac.in/org_farm/orgfarm_tomato_harvest.html) (tomato).

Infrastructure sources:

- National Horticulture Board — [Integrated Cold Chain Availability Platform report](https://nhb.gov.in/IcapMap/ICAPMap_rpt.aspx) and [mapped project endpoint](https://nhb.gov.in/Handlers/GeoIndiaHandlerGis.ashx).
- Warehousing Development and Regulatory Authority — [public registered-warehouse list](https://wdra.gov.in/registered-wh-public).
- Ministry of Food Processing Industries — [Integrated Cold Chain and Value Addition Infrastructure scheme](https://mofpi.gov.in/en/Schemes/about-cold-chain), captured as scheme context only.
- [Project OSRM public routing service](https://router.project-osrm.org/) using OpenStreetMap road geometry, captured only as static collection-date route context for tomato/NHB coordinate pairs.

## Data artifacts

| File | Role |
| --- | --- |
| [postharvest_source_inventory.csv](postharvest_source_inventory.csv) | Final source register for this enrichment; every raw snapshot is hash-linked. |
| [postharvest_handling_profiles.csv](postharvest_handling_profiles.csv) | One safe post-harvest profile per crop. |
| [postharvest_operation_library.csv](postharvest_operation_library.csv) | Source-quoted operation, method/parameter, missing observation, and source locator. |
| [postharvest_nhb_facility_records.csv](postharvest_nhb_facility_records.csv) | NHB mapped project coordinates for benchmark states. |
| [postharvest_nhb_state_infrastructure.csv](postharvest_nhb_state_infrastructure.csv) | NHB state-level component totals. |
| [postharvest_wdra_warehouse_records.csv](postharvest_wdra_warehouse_records.csv) | WDRA public registry metadata. |
| [postharvest_site_facility_context.csv](postharvest_site_facility_context.csv) | Transparent site-to-directory candidate links. |
| [postharvest_static_route_context.csv](postharvest_static_route_context.csv) | Cached static OSRM geometry for the tomato/NHB candidate links; never a live routing signal. |
| [postharvest_site_summary.csv](postharvest_site_summary.csv) | One summary per frozen study site. |
| [scenario_postharvest_plan_items.csv](scenario_postharvest_plan_items.csv) | Crop-scoped conditional plan items for all 300 scenarios. |
| [scenario_postharvest_logistics_context.csv](scenario_postharvest_logistics_context.csv) | One post-harvest context object per scenario. |
| [postharvest_rag_passages.csv](postharvest_rag_passages.csv) | Immutable quoted RAG passages. |
| [scenario_postharvest_rag_scope.csv](scenario_postharvest_rag_scope.csv) | Exact crop-filtered RAG allow-list; do not bypass it. |
| [postharvest_logistics_provenance.csv](postharvest_logistics_provenance.csv) | Build inputs and raw-source provenance. |

## Integration contract for the future agent

`postharvest_storage_logistics_agent` consumes only the requested scenario's rows from:

1. `scenario_postharvest_logistics_context.csv`;
2. `scenario_postharvest_plan_items.csv`;
3. `postharvest_site_summary.csv` and `postharvest_site_facility_context.csv`; and
4. `postharvest_rag_passages.csv` **after** applying `scenario_postharvest_rag_scope.csv`.

Its decision status remains `conditional_postharvest_plan_not_direct_farm_action`.
It deterministically orders plan items by the frozen crop-handling sequence and
source specificity. It must not convert an infrastructure candidate into a
facility recommendation or a booking instruction.

Suggested concise farmer output when the required lot observation is absent:

> **Post-harvest plan:** The regional handling reference for this crop contains the cited maturity, drying, grading, packing, or storage steps. These steps apply only after the corresponding lot condition is confirmed. Public registry candidates are shown as infrastructure context, not as confirmed available services.

When field or facility observations later become available, they should enter as a new time-stamped evidence layer rather than overwriting this frozen public-source enrichment.

## Reproducibility and audit

Build the artifacts with:

```bash
python3 scripts/build_postharvest_logistics_enrichment.py
python3 scripts/audit_postharvest_logistics_enrichment.py
pytest -q tests/test_postharvest_logistics_enrichment.py
```

Use `--refresh` only when deliberately collecting a new public infrastructure snapshot. A refresh changes the collection-date directory and should be reviewed, audited, and versioned; it must never silently alter frozen scenario facts.

The audit in [POSTHARVEST_LOGISTICS_AUDIT.md](POSTHARVEST_LOGISTICS_AUDIT.md) checks source hashes, six-crop coverage, source quotations, infrastructure safety boundaries, 30-site consistency, 300-scenario bindings, and exact-crop RAG scoping.
