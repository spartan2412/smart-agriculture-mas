# Table 8. Source-traceable farmer-facing and conflict-resolution case studies

The six normal cases are one anchor scenario per crop from the saved E0/E1 paired-output comparison. Each retains its decision status, direct-action flag, and citation set across E0 and E1; E1 only changes bounded presentation/selection. The final conflict case is explicitly evaluation-only and never appears as a farmer message.

## Rice — Bathinda, Punjab (2025-11-30)

- Scenario: `ANCHOR_PF_PB_BATHINDA_RICE_KHARIF_20251130`
- Decision status: `conditional_operation_pending_field_precondition`
- Direct farm action: `False`
- Source IDs in decision trace: AGMARKNET_MONTHLY_REPORT, CIBRC_INSECTICIDE_2026, FROZEN_SCENARIO_MANIFEST, ICAR_CRIDA_CCP, ICAR_CRIDA_PB_BATHINDA_CONTINGENCY, ICAR_CRIDA_PB_BATHINDA_CROP_PROFILE, ICAR_CRIDA_PB_BATHINDA_SOWING_WINDOW, MAS_ENRICHMENT_CONTRACT, NASA_POWER_HISTORICAL_WINDOW, NATURAL_SIGNAL_DIVERGENCE, PAU_ARCHIVE_KHARIF_2025, PAU_KHARIF_2026, SENTINEL2_L2A, SOILGRIDS, WDRA_REGISTERED_WAREHOUSES_PUNJAB
- E0/E1 citation set unchanged: `True`; message exact match: `False`.

**Saved E1 farmer-facing plan**

> Scenario: Rice in Bathinda, Punjab (2025-11-30).
> **Regional seasonal planning window**
>   - Regional guidance: The declared kharif window for this crop and district is Jun-Nov; the scenario date falls in the late part of that window.
>   - Required scope or condition: The position is derived only from the declared district-scale season window and decision month. It is not an observed sowing date or field phenology stage.
>   - Not established by this scenario: actual_crop_stage_not_observed.
>   - Planning status: regional_planning_context_not_observed_field_stage.
>   - Source: District crop profile and sowing-window evidence — ICAR_CRIDA_CCP — ICAR-CRIDA.
>   - Source location: District CCP crop profile and sowing-window PDFs.
>   - Source URL: https://icar-crida.res.in/CCP/PB/Bathinda/1.7.pdf;https://icar-crida.res.in/CCP/PB/Bathinda/1.12.pdf
> Source-scoped regional operation: Post-harvest plan — Harvest Readiness: Harvest at proper maturity and variety-wise; avoid night harvesting. It is not issued as a farm action; apply it only when its documented field condition is observed. Required condition: Use only when the rice crop's proper variety-specific maturity is actually observed. Source: PAU_KHARIF_2026.
> **Conditional official operation — Official conditional operation**
>   - Regional guidance: Harvesting should be done at proper maturity and variety-wise. Avoid harvesting during night.
>   - Method: Avoid harvesting during night.
>   - Required scope or condition: Only when proper maturity is observed for the variety.
>   - Not established by this scenario: actual_crop_stage.
>   - Current status: not issued as a farm action; it remains conditional until the required condition is observed.
>   - Source wording: Harvesting should be done at proper maturity and variety-wise. Avoid harvesting during night.
>   - Source: Package of Practices for Crops of Punjab — Kharif 2025 — PAU_ARCHIVE_KHARIF_2025 — Punjab Agricultural University.
>   - Source location: pdf_page_11.
>   - Source URL: https://www.pau.edu/content/ccil/pf/pp_kharif.pdf
> **Conditional official operation — Official conditional operation**
>   - Regional guidance: Stop irrigation about a fortnight before maturity.
>   - Required scope or condition: Only when the crop is about a fortnight before maturity.
>   - Not established by this scenario: actual_crop_stage.
>   - Current status: not issued as a farm action; it remains conditional until the required condition is observed.
>   - Source wording: Stop irrigation about a fortnight before maturity.
>   - Source: Package of Practices for Crops of Punjab — Kharif 2025 — PAU_ARCHIVE_KHARIF_2025 — Punjab Agricultural University.
>   - Source location: pdf_page_11.
>   - Source URL: https://www.pau.edu/content/ccil/pf/pp_kharif.pdf
> **Regional nutrient planning reference**
>   - Regional guidance: Use the cited Punjab rice regional fertilizer source as a planning reference. The system preserves the documented scope and does not convert it into a farm-specific prescription or treatment order.
>   - Source-recorded regional schedule: For PAU rice varieties other than PR 132: N 42, P2O5 12 and K2O 12 kg/acre; the source lists neem-coated urea 90 kg, DAP 27 kg or single superphosphate 75 kg, and MOP 20 kg/acre. It divides N into three equal applications: within 7 days of transplanting, 21 DAT, then 35 DAT for PR 126 or 42 DAT for other varieties.
>   - Source-recorded applicability: Regional Punjab rice reference only. P and K remain conditional on the source's soil-test provisions; the crop variety, observed stage, prior application and field soil test are not recorded here.
>   - Safety boundary: This is a source-recorded regional schedule, not permission to issue an individual field dose.
>   - Required scope or condition: Regional fallback only; PAU soil-test conditions and diagnosis thresholds remain mandatory.
>   - Not established by this scenario: actual_crop_stage_and_field_soil_test_not_observed.
>   - Safety boundary: This remains a regional policy reference; no field-specific dose is issued.
>   - Source: Package of Practices for Crops of Punjab — Kharif 2026 — PAU_KHARIF_2026 — Punjab Agricultural University.
>   - Source location: PDF p. 10 rice nutrient schedule.
>   - Source URL: https://www.pau.edu/content/ccil/pf/pp_kharif.pdf
> **Regional IPM planning reference**
>   - Regional guidance: Use the cited Punjab rice regional protection source as a planning reference. The system preserves the documented scope and does not convert it into a farm-specific prescription or treatment order.
>   - Source-recorded IPM method/options: For rice stem borer, the source records a more-than-5%-dead-hearts threshold and chlorantraniliprole 18.5% SC at 60 mL/acre in 100 L water, with repetition only if damage again reaches that threshold. For sheath blight, it first records residue/bund management and avoiding excessive nitrogen; where the disease appears at maximum tillering to boot stage, it records propiconazole 25% EC at 200 mL/acre in 200 L water, with a second spray only when required after 15 days.
>   - Source-recorded applicability: The applicable problem, threshold or diagnosis, crop stage and field condition are not recorded by this scenario. These are conditional IPM/treatment references, never a calendar spray.
>   - Safety boundary: Do not interpret either source-recorded option as a treatment order.
>   - Required scope or condition: Regional fallback only; PAU soil-test conditions and diagnosis thresholds remain mandatory.
>   - Not established by this scenario: dated_diagnosis_or_threshold_event_not_observed.
>   - Planning status: conditional_IPM_policy_only_diagnosis_or_threshold_event_required.
>   - Source: Package of Practices for Crops of Punjab — Kharif 2026 — PAU_KHARIF_2026 — Punjab Agricultural University.
>   - Source location: PDF pp. 14-15 stem-borer ETL and p. 17 sheath-blight action.
>   - Source URL: https://www.pau.edu/content/ccil/pf/pp_kharif.pdf
> **Post-harvest plan — Harvest Readiness**
>   - Operation: Harvest at proper maturity and variety-wise; avoid night harvesting.
>   - Required lot/harvest condition: Use only when the rice crop's proper variety-specific maturity is actually observed.
>   - Not established by this scenario: actual_crop_maturity_and_harvest_readiness_not_observed.
>   - Current status: conditional planning reference, not a harvest, storage, transport, or dispatch instruction.
>   - Source wording: Harvesting should be done at proper maturity and variety-wise. Avoid harvesting during night.
>   - Source: Package of Practices for Crops of Punjab — Kharif 2026 — PAU_KHARIF_2026.
>   - Source location: pdf_page_9.
>   - Source URL: https://www.pau.edu/content/ccil/pf/pp_kharif.pdf
> **Post-harvest plan — Dry Storage**
>   - Operation: Dry the harvested produce well before storage; keep produce intended for storage in appropriate bins.
>   - Method or parameter: The cited Punjab package states an optimum paddy storage moisture content of 12%.
>   - Required lot/harvest condition: Only after harvest and a lot-specific moisture/quality check; this does not establish the actual lot moisture.
>   - Not established by this scenario: harvested_lot_moisture_and_storage_condition_not_observed.
>   - Current status: conditional planning reference, not a harvest, storage, transport, or dispatch instruction.
>   - Source wording: Dry the produce well and store separately in disinfested bins. The produce kept for home use should be dried thoroughly in the sun for about a week and stored in bins or kept in a heap inside the room. The optimum moisture content for storage is 12 per cent.
>   - Source: Package of Practices for Crops of Punjab — Kharif 2026 — PAU_KHARIF_2026.
>   - Source location: pdf_page_20.
>   - Source URL: https://www.pau.edu/content/ccil/pf/pp_kharif.pdf
> **Storage/logistics context: source-linked facility and warehouse candidates**
>   - These are collection-date public-directory or mapped-project records, not a live availability, booking, commodity-acceptance, freight, or dispatch instruction.
>   1. **CENTRAL WAREHOUSE BATHINDA**
>      - Source record ID: WDRA_PUNJAB_4573874.
>      - Record type: wdra_registered_warehouse_district_match.
>      - Recorded location: Bathinda, Punjab.
>      - Captured registry status: Active.
>      - Listed registry capacity: 44660 MT; this is not current vacant capacity.
>      - Record scope: Collection-date WDRA registration context; no facility coordinates are exposed by this public registry response.
>      - Not established: No claim of commodity acceptance, current or historical capacity, vacancy, booking, quality, transport, freight, or storage duration.
>      - Source: WDRA_REGISTERED_WAREHOUSES_PUNJAB.
>      - Source URL: https://wdra.gov.in/registered-wh-public
>   2. **Globus Warehousing and Trading Private Limited**
>      - Source record ID: WDRA_PUNJAB_6984066.
>      - Record type: wdra_registered_warehouse_district_match.
>      - Recorded location: Bathinda, Punjab.
>      - Captured registry status: Active.
>      - Listed registry capacity: 37500 MT; this is not current vacant capacity.
>      - Record scope: Collection-date WDRA registration context; no facility coordinates are exposed by this public registry response.
>      - Not established: No claim of commodity acceptance, current or historical capacity, vacancy, booking, quality, transport, freight, or storage duration.
>      - Source: WDRA_REGISTERED_WAREHOUSES_PUNJAB.
>      - Source URL: https://wdra.gov.in/registered-wh-public
>   3. **Bansal Godowns**
>      - Source record ID: WDRA_PUNJAB_6838536.
>      - Record type: wdra_registered_warehouse_district_match.
>      - Recorded location: Bathinda, Punjab.
>      - Captured registry status: Inactive.
>      - Listed registry capacity: 20000 MT; this is not current vacant capacity.
>      - Record scope: Collection-date WDRA registration context; no facility coordinates are exposed by this public registry response.
>      - Not established: No claim of commodity acceptance, current or historical capacity, vacancy, booking, quality, transport, freight, or storage duration.
>      - Source: WDRA_REGISTERED_WAREHOUSES_PUNJAB.
>      - Source URL: https://wdra.gov.in/registered-wh-public
> **Historical weather and water context**
>   - Historical decision window: 2025-11-01T00:00:00Z/2025-11-30T23:59:59Z; source-observed days: 30.
>   - Air context: mean temperature 18.680 °C; relative humidity 41.100%; wind speed 1.308 m/s; shortwave radiation 14.232 MJ/m²/day.
>   - Water context: precipitation 0.320 mm; modelled root-zone wetness mean/min/max 0.480/0.460/0.510; modelled top-layer wetness mean 0.423.
>   - Water-balance context: land evaporation 26.000 mm; precipitation minus land evaporation -25.680 mm.
>   - Scope: NASA POWER AG retrospective representative-cell context. GWETROOT/GWETTOP and EVLAND are source-modelled variables; precipitation minus land evaporation is an aggregated context indicator, not a field water balance, irrigation dose, or forecast.
>   - Decision boundary: this is retrospective representative-cell context, not current field moisture, an irrigation history, or a forecast.
>   - Source: NASA POWER historical weather and modelled water context — NASA_POWER_HISTORICAL_WINDOW.
>   - Source location: 2025-11-01T00:00:00Z/2025-11-30T23:59:59Z.
>   - Source URL: https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M%2CPRECTOTCORR%2CRH2M%2CWS2M&community=AG&longitude=75.004814&latitude=30.178658&start=20251101&end=20251130&format=JSON
> **Static SoilGrids context (representative cell, 0–5 cm)**
>   - Clay 0-5cm mean (g/kg): source-reported raw value 197. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fclay.map&request=GetMetadata&layer=clay_0-5cm_mean
>   - Nitrogen 0-5cm mean (cg/kg): source-reported raw value 141. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fnitrogen.map&request=GetMetadata&layer=nitrogen_0-5cm_mean
>   - Organic carbon density 0-5cm mean (hg/m3): source-reported raw value 184. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Focd.map&request=GetMetadata&layer=ocd_0-5cm_mean
>   - pH in H2O 0-5cm mean (pH*10): source-reported raw value 78. Metadata title states pH*10; raw_value_divided_by_10_is_pH.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fphh2o.map&request=GetMetadata&layer=phh2o_0-5cm_mean
>   - Sand 0-5cm mean (g/kg): source-reported raw value 424. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fsand.map&request=GetMetadata&layer=sand_0-5cm_mean
>   - Silt 0-5cm mean (g/kg): source-reported raw value 379. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fsilt.map&request=GetMetadata&layer=silt_0-5cm_mean
>   - Decision boundary: these are static gridded predictors at a documented representative cell, not a field soil test, current moisture measurement, or plant-available farm N/P/K result.
>   - Source: ISRIC SoilGrids static 0–5 cm profile — SOILGRIDS.
>   - Source location: public_worldcover_cropland_documented_representative_cell.
>   - Source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fphh2o.map&request=GetMetadata&layer=phh2o_0-5cm_mean
> **Historical Sentinel-2 / NDVI context (representative cell)**
>   - Scene: S2C_MSIL2A_20251127T054211_R005_T43REP_20251127T104409 acquired 2025-11-27T05:42:11.025000Z; pixel class 5 (not_vegetated); quality clear_surface_pixel.
>   - Scene values: red DN 2136; NIR DN 2688; NDVI 0.114428.
>   - Pre-decision chronology: 4 clear observations from 2025-09-10T05:42:41.024000Z to 2025-11-29T05:42:51.024000Z (80.000 days); first/last NDVI 0.618545/0.108076; change -0.510469; slope -0.00625699 per day; recorded trend decrease_at_least_0_05_ndvi.
>   - Source record: Microsoft_Planetary_Computer_STAC; sentinel-2-l2a.
>   - Scope: NDVI is calculated as (B08 - B04) / (B08 + B04) from the exact selected Sentinel-2 L2A scene at the documented representative cropland coordinate.
>   - Decision boundary: this is not evidence of crop identity, field condition, crop stage, disease, nutrient status, or irrigation need.
>   - Source: Sentinel-2 L2A representative-cell context — SENTINEL2_L2A.
>   - Source location: S2C_MSIL2A_20251127T054211_R005_T43REP_20251127T104409.
>   - Source URL: https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a/items/S2C_MSIL2A_20251127T054211_R005_T43REP_20251127T104409
> **Historical nearest-mandi market context**
>   - Exact report values: decision-month mean 2389.000; prior-month mean 2389.000 (0.000% change); same-month prior-year mean 2320.000 (2.974% change).
>   - Report availability: prior_month_and_same_month_prior_year; price-unit status as_reported_by_agmarknet_monthly_API_no_unit_inference; source commodity Paddy(Common) in Bhatinda, Punjab.
>   - Scope: Means and percentage changes use price columns published in the exact frozen official monthly report. They are retrospective context, not a price forecast or sell/hold instruction.
>   - Decision boundary: the official monthly report supports historical comparison only; it contains no crop quality, storage cost, quantity, or forecast
>   - Source: Agmarknet historical monthly report context — AGMARKNET_MONTHLY_REPORT.
>   - Source location: decision date 2025-11-30.
>   - Source URL: https://api.agmarknet.gov.in/v1/price-trend/wholesale-prices-monthly?report_mode=Marketwise&commodity=2&year=2025&month=11&state=28&district=454
> Direct irrigation, farm-specific fertilizer, and treatment decisions remain gated by missing field evidence.
> Evidence trace: AGMARKNET_MONTHLY_REPORT, CIBRC_INSECTICIDE_2026, FROZEN_SCENARIO_MANIFEST, ICAR_CRIDA_CCP, ICAR_CRIDA_PB_BATHINDA_CONTINGENCY, ICAR_CRIDA_PB_BATHINDA_CROP_PROFILE, ICAR_CRIDA_PB_BATHINDA_SOWING_WINDOW, MAS_ENRICHMENT_CONTRACT.

## Wheat — Bathinda, Punjab (2026-04-30)

- Scenario: `ANCHOR_PF_PB_BATHINDA_WHEAT_RABI_20260430`
- Decision status: `conditional_operation_pending_field_precondition`
- Direct farm action: `False`
- Source IDs in decision trace: AGMARKNET_MONTHLY_REPORT, CIBRC_FUNGICIDE_2026, FROZEN_SCENARIO_MANIFEST, ICAR_CRIDA_CCP, MAS_ENRICHMENT_CONTRACT, NASA_POWER_HISTORICAL_WINDOW, NATURAL_SIGNAL_DIVERGENCE, PAU_RABI_2025_26, SENTINEL2_L2A, SOILGRIDS, WDRA_REGISTERED_WAREHOUSES_PUNJAB
- E0/E1 citation set unchanged: `True`; message exact match: `False`.

**Saved E1 farmer-facing plan**

> Scenario: Wheat in Bathinda, Punjab (2026-04-30).
> **Regional seasonal planning window**
>   - Regional guidance: The declared rabi window for this crop and district is Nov-Apr; the scenario date falls in the late part of that window.
>   - Required scope or condition: The position is derived only from the declared district-scale season window and decision month. It is not an observed sowing date or field phenology stage.
>   - Not established by this scenario: actual_crop_stage_not_observed.
>   - Planning status: regional_planning_context_not_observed_field_stage.
>   - Source: District crop profile and sowing-window evidence — ICAR_CRIDA_CCP — ICAR-CRIDA.
>   - Source location: District CCP crop profile and sowing-window PDFs.
>   - Source URL: https://icar-crida.res.in/CCP/PB/Bathinda/1.7.pdf;https://icar-crida.res.in/CCP/PB/Bathinda/1.12.pdf
> Source-scoped regional operation: Post-harvest plan — Harvest Readiness: Harvest and thresh wheat as soon as it is fully ripe to avoid shattering losses. It is not issued as a farm action; apply it only when its documented field condition is observed. Required condition: Only when full wheat maturity is actually observed. Source: PAU_RABI_2025_26.
> **Conditional official operation — Official conditional operation**
>   - Regional guidance: Harvest and thresh wheat as soon as fully ripe, to avoid grain shattering.
>   - Method: Harvest manually, with a combine, or with a tractor-operated vertical conveyer reaper windrower as documented in the source.
>   - Required scope or condition: Only when the wheat is fully ripe.
>   - Not established by this scenario: actual_crop_stage.
>   - Current status: not issued as a farm action; it remains conditional until the required condition is observed.
>   - Source wording: Harvest and thresh wheat as soon as fully ripe, to avoid grain shattering. Delayed harvesting results in high grain losses.
>   - Source: Package of Practices for Crops of Punjab — Rabi 2025–26 — PAU_RABI_2025_26 — Punjab Agricultural University.
>   - Source location: pdf_page_25.
>   - Source URL: https://pau.edu/content/ccil/pf/pp_rabi.pdf
> **Regional nutrient planning reference**
>   - Regional guidance: Use the cited Punjab wheat regional fertilizer source as a planning reference. The system preserves the documented scope and does not convert it into a farm-specific prescription or treatment order.
>   - Source-recorded regional schedule: For Punjab medium-fertility wheat, the source records N 50 and P2O5 25 kg/acre; it lists neem-coated urea 110 kg and DAP 55 kg or single superphosphate 155 kg/acre. K2O is only for a documented low-K soil: 12 kg/acre (20 kg MOP), except 24 kg K2O/acre in Gurdaspur, Hoshiarpur, Rupnagar and SBS Nagar. The source places P and any K at sowing and urea at the first and second irrigation.
>   - Source-recorded applicability: Regional medium-fertility reference only. Soil-K status, actual sowing, irrigation, crop stage and prior nutrient application are not recorded by this scenario.
>   - Safety boundary: This is a source-recorded regional schedule, not permission to issue an individual field dose.
>   - Required scope or condition: Regional fallback only; potassium and treatment decisions retain their source conditions.
>   - Not established by this scenario: actual_crop_stage_and_field_soil_test_not_observed.
>   - Safety boundary: This remains a regional policy reference; no field-specific dose is issued.
>   - Source: Package of Practices for Crops of Punjab — Rabi 2025–26 — PAU_RABI_2025_26 — Punjab Agricultural University.
>   - Source location: PDF pp. 9-10 wheat nutrient schedule.
>   - Source URL: https://pau.edu/content/ccil/pf/pp_rabi.pdf
> **Regional IPM planning reference**
>   - Regional guidance: Use the cited Punjab wheat regional protection source as a planning reference. The system preserves the documented scope and does not convert it into a farm-specific prescription or treatment order.
>   - Source-recorded IPM method/options: For confirmed yellow/stripe rust, PAU records resistant varieties, monitoring from the second week of December and initial spot treatment around infected patches. It records propiconazole 25% EC at 200 mL/acre in 200 L water as soon as disease is noticed, initially around infected patches, with repetition only as needed.
>   - Source-recorded applicability: A dated yellow-rust diagnosis, observed crop stage, infected-patch status and field condition are not recorded by this scenario.
>   - Safety boundary: This source-recorded option is conditional IPM context, not a treatment order.
>   - Required scope or condition: Regional fallback only; potassium and treatment decisions retain their source conditions.
>   - Not established by this scenario: dated_diagnosis_or_threshold_event_not_observed.
>   - Planning status: conditional_IPM_policy_only_diagnosis_or_threshold_event_required.
>   - Source: Package of Practices for Crops of Punjab — Rabi 2025–26 — PAU_RABI_2025_26 — Punjab Agricultural University.
>   - Source location: PDF pp. 19-20 yellow-rust action.
>   - Source URL: https://pau.edu/content/ccil/pf/pp_rabi.pdf
> **Post-harvest plan — Harvest Readiness**
>   - Operation: Harvest and thresh wheat as soon as it is fully ripe to avoid shattering losses.
>   - Required lot/harvest condition: Only when full wheat maturity is actually observed.
>   - Not established by this scenario: actual_crop_maturity_not_observed.
>   - Current status: conditional planning reference, not a harvest, storage, transport, or dispatch instruction.
>   - Source wording: Harvest and thresh wheat as soon as fully ripe, to avoid grain shattering. Delayed harvesting results in high grain losses.
>   - Source: Package of Practices for Crops of Punjab — Rabi 2025–26 — PAU_RABI_2025_26.
>   - Source location: pdf_page_25.
>   - Source URL: https://pau.edu/content/ccil/pf/pp_rabi.pdf
> **Post-harvest plan — Dry Storage**
>   - Operation: Dry grain before storage when its moisture exceeds the cited threshold.
>   - Method or parameter: The cited Punjab package gives a 10% grain-moisture threshold.
>   - Required lot/harvest condition: Only after a lot-specific moisture measurement; the benchmark does not contain one.
>   - Not established by this scenario: harvested_lot_moisture_not_observed.
>   - Current status: conditional planning reference, not a harvest, storage, transport, or dispatch instruction.
>   - Source wording: In case the grain contains more than 10 per cent moisture, it should be dried before storing, otherwise it would be spoiled by moulds and excessive heat that develops during storage.
>   - Source: Package of Practices for Crops of Punjab — Rabi 2025–26 — PAU_RABI_2025_26.
>   - Source location: pdf_page_25.
>   - Source URL: https://pau.edu/content/ccil/pf/pp_rabi.pdf
> **Storage/logistics context: source-linked facility and warehouse candidates**
>   - These are collection-date public-directory or mapped-project records, not a live availability, booking, commodity-acceptance, freight, or dispatch instruction.
>   1. **CENTRAL WAREHOUSE BATHINDA**
>      - Source record ID: WDRA_PUNJAB_4573874.
>      - Record type: wdra_registered_warehouse_district_match.
>      - Recorded location: Bathinda, Punjab.
>      - Captured registry status: Active.
>      - Listed registry capacity: 44660 MT; this is not current vacant capacity.
>      - Record scope: Collection-date WDRA registration context; no facility coordinates are exposed by this public registry response.
>      - Not established: No claim of commodity acceptance, current or historical capacity, vacancy, booking, quality, transport, freight, or storage duration.
>      - Source: WDRA_REGISTERED_WAREHOUSES_PUNJAB.
>      - Source URL: https://wdra.gov.in/registered-wh-public
>   2. **Globus Warehousing and Trading Private Limited**
>      - Source record ID: WDRA_PUNJAB_6984066.
>      - Record type: wdra_registered_warehouse_district_match.
>      - Recorded location: Bathinda, Punjab.
>      - Captured registry status: Active.
>      - Listed registry capacity: 37500 MT; this is not current vacant capacity.
>      - Record scope: Collection-date WDRA registration context; no facility coordinates are exposed by this public registry response.
>      - Not established: No claim of commodity acceptance, current or historical capacity, vacancy, booking, quality, transport, freight, or storage duration.
>      - Source: WDRA_REGISTERED_WAREHOUSES_PUNJAB.
>      - Source URL: https://wdra.gov.in/registered-wh-public
>   3. **Bansal Godowns**
>      - Source record ID: WDRA_PUNJAB_6838536.
>      - Record type: wdra_registered_warehouse_district_match.
>      - Recorded location: Bathinda, Punjab.
>      - Captured registry status: Inactive.
>      - Listed registry capacity: 20000 MT; this is not current vacant capacity.
>      - Record scope: Collection-date WDRA registration context; no facility coordinates are exposed by this public registry response.
>      - Not established: No claim of commodity acceptance, current or historical capacity, vacancy, booking, quality, transport, freight, or storage duration.
>      - Source: WDRA_REGISTERED_WAREHOUSES_PUNJAB.
>      - Source URL: https://wdra.gov.in/registered-wh-public
> **Historical weather and water context**
>   - Historical decision window: 2026-04-01T00:00:00Z/2026-04-30T23:59:59Z; source-observed days: 30.
>   - Air context: mean temperature 29.123 °C; relative humidity 34.907%; wind speed 1.982 m/s; shortwave radiation 22.211 MJ/m²/day.
>   - Water context: precipitation 16.450 mm; modelled root-zone wetness mean/min/max 0.454/0.450/0.470; modelled top-layer wetness mean 0.288.
>   - Water-balance context: land evaporation 22.120 mm; precipitation minus land evaporation -5.670 mm.
>   - Scope: NASA POWER AG retrospective representative-cell context. GWETROOT/GWETTOP and EVLAND are source-modelled variables; precipitation minus land evaporation is an aggregated context indicator, not a field water balance, irrigation dose, or forecast.
>   - Decision boundary: this is retrospective representative-cell context, not current field moisture, an irrigation history, or a forecast.
>   - Source: NASA POWER historical weather and modelled water context — NASA_POWER_HISTORICAL_WINDOW.
>   - Source location: 2026-04-01T00:00:00Z/2026-04-30T23:59:59Z.
>   - Source URL: https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M%2CPRECTOTCORR%2CRH2M%2CWS2M&community=AG&longitude=75.004814&latitude=30.178658&start=20260401&end=20260430&format=JSON
> **Static SoilGrids context (representative cell, 0–5 cm)**
>   - Clay 0-5cm mean (g/kg): source-reported raw value 197. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fclay.map&request=GetMetadata&layer=clay_0-5cm_mean
>   - Nitrogen 0-5cm mean (cg/kg): source-reported raw value 141. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fnitrogen.map&request=GetMetadata&layer=nitrogen_0-5cm_mean
>   - Organic carbon density 0-5cm mean (hg/m3): source-reported raw value 184. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Focd.map&request=GetMetadata&layer=ocd_0-5cm_mean
>   - pH in H2O 0-5cm mean (pH*10): source-reported raw value 78. Metadata title states pH*10; raw_value_divided_by_10_is_pH.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fphh2o.map&request=GetMetadata&layer=phh2o_0-5cm_mean
>   - Sand 0-5cm mean (g/kg): source-reported raw value 424. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fsand.map&request=GetMetadata&layer=sand_0-5cm_mean
>   - Silt 0-5cm mean (g/kg): source-reported raw value 379. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fsilt.map&request=GetMetadata&layer=silt_0-5cm_mean
>   - Decision boundary: these are static gridded predictors at a documented representative cell, not a field soil test, current moisture measurement, or plant-available farm N/P/K result.
>   - Source: ISRIC SoilGrids static 0–5 cm profile — SOILGRIDS.
>   - Source location: public_worldcover_cropland_documented_representative_cell.
>   - Source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fphh2o.map&request=GetMetadata&layer=phh2o_0-5cm_mean
> **Historical Sentinel-2 / NDVI context (representative cell)**
>   - Scene: S2C_MSIL2A_20260426T053641_R005_T43REP_20260426T101812 acquired 2026-04-26T05:36:41.025000Z; pixel class 5 (not_vegetated); quality clear_surface_pixel.
>   - Scene values: red DN 3625; NIR DN 4391; NDVI 0.095559.
>   - Pre-decision chronology: 4 clear observations from 2026-01-31T05:39:49.024000Z to 2026-04-26T05:36:41.025000Z (84.998 days); first/last NDVI 0.621128/0.093090; change -0.528038; slope -0.00678327 per day; recorded trend decrease_at_least_0_05_ndvi.
>   - Source record: Microsoft_Planetary_Computer_STAC; sentinel-2-l2a.
>   - Scope: NDVI is calculated as (B08 - B04) / (B08 + B04) from the exact selected Sentinel-2 L2A scene at the documented representative cropland coordinate.
>   - Decision boundary: this is not evidence of crop identity, field condition, crop stage, disease, nutrient status, or irrigation need.
>   - Source: Sentinel-2 L2A representative-cell context — SENTINEL2_L2A.
>   - Source location: S2C_MSIL2A_20260426T053641_R005_T43REP_20260426T101812.
>   - Source URL: https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a/items/S2C_MSIL2A_20260426T053641_R005_T43REP_20260426T101812
> **Historical nearest-mandi market context**
>   - Exact report values: decision-month mean 2585.000; prior-month mean  (% change); same-month prior-year mean 2425.000 (6.598% change).
>   - Report availability: same_month_prior_year_only; price-unit status as_reported_by_agmarknet_monthly_API_no_unit_inference; source commodity Wheat in Bhatinda, Punjab.
>   - Scope: Means and percentage changes use price columns published in the exact frozen official monthly report. They are retrospective context, not a price forecast or sell/hold instruction.
>   - Decision boundary: the official monthly report supports historical comparison only; it contains no crop quality, storage cost, quantity, or forecast
>   - Source: Agmarknet historical monthly report context — AGMARKNET_MONTHLY_REPORT.
>   - Source location: decision date 2026-04-30.
>   - Source URL: https://api.agmarknet.gov.in/v1/price-trend/wholesale-prices-monthly?report_mode=Marketwise&commodity=1&year=2026&month=4&state=28&district=454
> Direct irrigation, farm-specific fertilizer, and treatment decisions remain gated by missing field evidence.
> Evidence trace: AGMARKNET_MONTHLY_REPORT, CIBRC_FUNGICIDE_2026, FROZEN_SCENARIO_MANIFEST, ICAR_CRIDA_CCP, MAS_ENRICHMENT_CONTRACT, NASA_POWER_HISTORICAL_WINDOW, NATURAL_SIGNAL_DIVERGENCE, PAU_RABI_2025_26.

## Maize — Ariyalur, Tamil Nadu (2026-03-31)

- Scenario: `ANCHOR_PF_TN_ARIYALUR_MAIZE_RABI_20260331`
- Decision status: `conditional_operation_pending_field_precondition`
- Direct farm action: `False`
- Source IDs in decision trace: AGMARKNET_MONTHLY_REPORT, CIBRC_INSECTICIDE_2026, FROZEN_SCENARIO_MANIFEST, ICAR_CRIDA_CCP, ICAR_CRIDA_TN_ARIYALUR_CROP_PROFILE, ICAR_CRIDA_TN_ARIYALUR_SOWING_WINDOW, ICAR_RABI_STATE_ADVISORIES_2021_22, MAS_ENRICHMENT_CONTRACT, NASA_POWER_HISTORICAL_WINDOW, NATURAL_SIGNAL_DIVERGENCE, SENTINEL2_L2A, SOILGRIDS, TNAU_MAIZE_FAW_2023, WDRA_REGISTERED_WAREHOUSES_TAMIL_NADU
- E0/E1 citation set unchanged: `True`; message exact match: `False`.

**Saved E1 farmer-facing plan**

> Scenario: Maize in Ariyalur, Tamil Nadu (2026-03-31).
> **Regional seasonal planning window**
>   - Regional guidance: The declared rabi window for this crop and district is Oct-Mar; the scenario date falls in the late part of that window.
>   - Required scope or condition: The position is derived only from the declared district-scale season window and decision month. It is not an observed sowing date or field phenology stage.
>   - Not established by this scenario: actual_crop_stage_not_observed.
>   - Planning status: regional_planning_context_not_observed_field_stage.
>   - Source: District crop profile and sowing-window evidence — ICAR_CRIDA_CCP — ICAR-CRIDA.
>   - Source location: District CCP crop profile and sowing-window PDFs.
>   - Source URL: https://icar-crida.res.in/CCP/TN/Ariyalur/1.7.pdf;https://icar-crida.res.in/CCP/TN/Ariyalur/1.12.pdf
> Source-scoped regional operation: Post-harvest plan — Harvest Readiness: Harvest maize when the husk cover has dried and turned brown; shell within the cited moisture range. It is not issued as a farm action; apply it only when its documented field condition is observed. Required condition: Only after observing husk condition and measuring grain moisture; neither is present in the scenario. Source: ICAR_RABI_STATE_ADVISORIES_2021_22.
> **Conditional official operation — Official conditional operation**
>   - Regional guidance: Use a source-listed FAW treatment only at the documented early stage.
>   - Method: Spray one of the listed source formulations.
>   - Source-recorded schedule/dose: Azadirachtin 1500 ppm 2.5 L/ha; or chlorantraniliprole 18.5 SC 200 ml/ha; or flubendiamide 480 SC 250 ml/ha.
>   - Required scope or condition: Only after supported FAW diagnosis/threshold and confirmed 15–20 days-after-emergence stage, with labelled/regulatory verification.
>   - Not established by this scenario: actual_crop_stage;dated_diagnosis_or_threshold.
>   - Current status: not issued as a farm action; it remains conditional until the required condition is observed.
>   - Source wording: Spray azadirachtin 1500 ppm @ 2.5 lit/ha or chlorantraniliprole 18.5 SC @ 200ml/ha (or) flubendiamide 480SC@ 250ml/ha at early stage (15 - 20 DAE).
>   - Source: TNAU fall-armyworm management in maize — TNAU_MAIZE_FAW_2023 — Tamil Nadu Agricultural University.
>   - Source location: html_document.
>   - Source URL: https://agritech.tnau.ac.in/crop_protection/maize/crop_prot_maize_fall_armyworm.html
> **Conditional official operation — Official conditional operation**
>   - Regional guidance: Set up FAW pheromone traps.
>   - Source-recorded schedule/dose: 12 traps/ha.
>   - Required scope or condition: Only for an existing maize crop when the implementation stage is documented.
>   - Not established by this scenario: actual_crop_stage.
>   - Current status: not issued as a farm action; it remains conditional until the required condition is observed.
>   - Source wording: Set up FAW pheromone traps @ 12 nos./ha
>   - Source: TNAU fall-armyworm management in maize — TNAU_MAIZE_FAW_2023 — Tamil Nadu Agricultural University.
>   - Source location: html_document.
>   - Source URL: https://agritech.tnau.ac.in/crop_protection/maize/crop_prot_maize_fall_armyworm.html
> **Regional nutrient planning reference**
>   - Regional guidance: Use the cited Tamil Nadu maize regional fertilizer source as a planning reference. The system preserves the documented scope and does not convert it into a farm-specific prescription or treatment order.
>   - Source-recorded regional schedule: For Tamil Nadu maize varieties, the source records N:P2O5:K2O = 135:62.5:50 kg/ha; for hybrids it records 250:75:75 kg/ha. It also records TNAU micronutrient mixture at 30 kg/ha as enriched FYM, prepared at a 1:10 micronutrient-mixture:FYM ratio, or 12.5 kg of the Department of Agriculture micronutrient mixture.
>   - Source-recorded applicability: The scenario does not record whether the crop is a variety or hybrid, actual crop stage, field soil test, FYM availability or previous nutrient application; no branch may be inferred.
>   - Safety boundary: These are source-recorded regional branches, not an individual field dose.
>   - Required scope or condition: Record variety or hybrid branch; FAW action is diagnosis-triggered and not a calendar spray.
>   - Not established by this scenario: actual_crop_stage_and_field_soil_test_not_observed.
>   - Safety boundary: This remains a regional policy reference; no field-specific dose is issued.
>   - Source: ICAR Rabi Agro-Advisory for Farmers 2021–22 — ICAR_RABI_STATE_ADVISORIES_2021_22 — Indian Council of Agricultural Research.
>   - Source location: PDF p. 390 Tamil Nadu maize NPK branches for varieties and hybrids.
>   - Source URL: https://icar.org.in/sites/default/files/2022-09/Rabi-Agro-Advisory-2021-22_0.pdf
> **Regional IPM planning reference**
>   - Regional guidance: Use the cited Tamil Nadu maize regional protection source as a planning reference. The system preserves the documented scope and does not convert it into a farm-specific prescription or treatment order.
>   - Source-recorded IPM method/options: The TNAU fall-armyworm page records neem cake at 250 kg/ha at last ploughing, cyantraniliprole 19.8% plus thiamethoxam 19.8% FS seed treatment at 4 mL/kg seed, border crops, and FAW pheromone traps at 12/ha. For an observed early FAW stage (15-20 DAE), it records azadirachtin 1500 ppm at 2.5 L/ha or chlorantraniliprole 18.5 SC at 200 mL/ha or flubendiamide 480 SC at 250 mL/ha. For observed late whorl stage (35-40 DAE), it records Metarhizium anisopliae at 2.5 kg/ha or emamectin benzoate 5 SG at 200 g/ha or novaluron 10 EC at 750 mL/ha or spinetoram 11.7 SC at 250 mL/ha.
>   - Source-recorded applicability: The scenario contains no FAW diagnosis, observed larval stage, crop age, threshold event, field condition or label-use decision. The page's stage-specific options remain conditional.
>   - Safety boundary: This is source-recorded IPM context, not a preventive or curative treatment order.
>   - Source-recorded detail location: HTML maize fall-armyworm management page.
>   - Required scope or condition: Record variety or hybrid branch; FAW action is diagnosis-triggered and not a calendar spray.
>   - Not established by this scenario: dated_diagnosis_or_threshold_event_not_observed.
>   - Planning status: conditional_IPM_policy_only_diagnosis_or_threshold_event_required.
>   - Source: TNAU fall-armyworm management in maize — TNAU_MAIZE_FAW_2023 — Tamil Nadu Agricultural University.
>   - Source location: HTML maize fall-armyworm page.
>   - Source URL: https://agritech.tnau.ac.in/crop_protection/maize/crop_prot_maize_fall_armyworm.html
> **Post-harvest plan — Harvest Readiness**
>   - Operation: Harvest maize when the husk cover has dried and turned brown; shell within the cited moisture range.
>   - Method or parameter: The cited ICAR reference gives a 15–20% shelling moisture range.
>   - Required lot/harvest condition: Only after observing husk condition and measuring grain moisture; neither is present in the scenario.
>   - Not established by this scenario: actual_husk_condition_and_harvested_lot_moisture_not_observed.
>   - Current status: conditional planning reference, not a harvest, storage, transport, or dispatch instruction.
>   - Source wording: Maize is ready for harvesting even when the stacks and leaves are somewhat green, but the husk cover has dried and turned brown. Shell Maize when the moisture content ranges between 15-20%.
>   - Source: ICAR Rabi Agro-Advisory for Farmers 2021–22 — ICAR_RABI_STATE_ADVISORIES_2021_22.
>   - Source location: pdf_page_151.
>   - Source URL: https://icar.org.in/sites/default/files/2022-09/Rabi-Agro-Advisory-2021-22_0.pdf
> **Post-harvest plan — Dry Storage**
>   - Operation: Dry maize ears after harvest before the next handling step.
>   - Method or parameter: The cited ICAR reference says ears should preferably be dried for 3–4 days after harvest.
>   - Required lot/harvest condition: Only after actual harvest; local drying conditions and lot moisture remain unobserved.
>   - Not established by this scenario: actual_harvest_status_lot_moisture_and_drying_conditions_not_observed.
>   - Current status: conditional planning reference, not a harvest, storage, transport, or dispatch instruction.
>   - Source wording: The Maize ears should preferably be dried for 3-4 days after harvesting to improve grain recoveries and reduce breakage losses.
>   - Source: ICAR Rabi Agro-Advisory for Farmers 2021–22 — ICAR_RABI_STATE_ADVISORIES_2021_22.
>   - Source location: pdf_page_151.
>   - Source URL: https://icar.org.in/sites/default/files/2022-09/Rabi-Agro-Advisory-2021-22_0.pdf
> **Storage/logistics context: source-linked facility and warehouse candidates**
>   - These are collection-date public-directory or mapped-project records, not a live availability, booking, commodity-acceptance, freight, or dispatch instruction.
>   1. **REGULATED MARKET - JAYAMKONDAM**
>      - Source record ID: WDRA_TAMIL_NADU_6629018.
>      - Record type: wdra_registered_warehouse_district_match.
>      - Recorded location: Ariyalur, Tamil Nadu.
>      - Captured registry status: Active.
>      - Listed registry capacity: 2000 MT; this is not current vacant capacity.
>      - Record scope: Collection-date WDRA registration context; no facility coordinates are exposed by this public registry response.
>      - Not established: No claim of commodity acceptance, current or historical capacity, vacancy, booking, quality, transport, freight, or storage duration.
>      - Source: WDRA_REGISTERED_WAREHOUSES_TAMIL_NADU.
>      - Source URL: https://wdra.gov.in/registered-wh-public
>   2. **REGULATED MARKET - ANDIMADAM**
>      - Source record ID: WDRA_TAMIL_NADU_6631535.
>      - Record type: wdra_registered_warehouse_district_match.
>      - Recorded location: Ariyalur, Tamil Nadu.
>      - Captured registry status: Active.
>      - Listed registry capacity: 2000 MT; this is not current vacant capacity.
>      - Record scope: Collection-date WDRA registration context; no facility coordinates are exposed by this public registry response.
>      - Not established: No claim of commodity acceptance, current or historical capacity, vacancy, booking, quality, transport, freight, or storage duration.
>      - Source: WDRA_REGISTERED_WAREHOUSES_TAMIL_NADU.
>      - Source URL: https://wdra.gov.in/registered-wh-public
>   3. **TYSPL 70 DEVAMANGALAM PACCS**
>      - Source record ID: WDRA_TAMIL_NADU_4560574.
>      - Record type: wdra_registered_warehouse_district_match.
>      - Recorded location: Ariyalur, Tamil Nadu.
>      - Captured registry status: Inactive.
>      - Listed registry capacity: 100 MT; this is not current vacant capacity.
>      - Record scope: Collection-date WDRA registration context; no facility coordinates are exposed by this public registry response.
>      - Not established: No claim of commodity acceptance, current or historical capacity, vacancy, booking, quality, transport, freight, or storage duration.
>      - Source: WDRA_REGISTERED_WAREHOUSES_TAMIL_NADU.
>      - Source URL: https://wdra.gov.in/registered-wh-public
> **Historical weather and water context**
>   - Historical decision window: 2026-03-01T00:00:00Z/2026-03-31T23:59:59Z; source-observed days: 31.
>   - Air context: mean temperature 28.323 °C; relative humidity 66.995%; wind speed 2.235 m/s; shortwave radiation 23.240 MJ/m²/day.
>   - Water context: precipitation 28.990 mm; modelled root-zone wetness mean/min/max 0.475/0.460/0.500; modelled top-layer wetness mean 0.398.
>   - Water-balance context: land evaporation 55.580 mm; precipitation minus land evaporation -26.590 mm.
>   - Scope: NASA POWER AG retrospective representative-cell context. GWETROOT/GWETTOP and EVLAND are source-modelled variables; precipitation minus land evaporation is an aggregated context indicator, not a field water balance, irrigation dose, or forecast.
>   - Decision boundary: this is retrospective representative-cell context, not current field moisture, an irrigation history, or a forecast.
>   - Source: NASA POWER historical weather and modelled water context — NASA_POWER_HISTORICAL_WINDOW.
>   - Source location: 2026-03-01T00:00:00Z/2026-03-31T23:59:59Z.
>   - Source URL: https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M%2CPRECTOTCORR%2CRH2M%2CWS2M&community=AG&longitude=79.225151&latitude=11.161771&start=20260301&end=20260331&format=JSON
> **Static SoilGrids context (representative cell, 0–5 cm)**
>   - Clay 0-5cm mean (g/kg): source-reported raw value 338. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fclay.map&request=GetMetadata&layer=clay_0-5cm_mean
>   - Nitrogen 0-5cm mean (cg/kg): source-reported raw value 230. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fnitrogen.map&request=GetMetadata&layer=nitrogen_0-5cm_mean
>   - Organic carbon density 0-5cm mean (hg/m3): source-reported raw value 292. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Focd.map&request=GetMetadata&layer=ocd_0-5cm_mean
>   - pH in H2O 0-5cm mean (pH*10): source-reported raw value 70. Metadata title states pH*10; raw_value_divided_by_10_is_pH.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fphh2o.map&request=GetMetadata&layer=phh2o_0-5cm_mean
>   - Sand 0-5cm mean (g/kg): source-reported raw value 370. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fsand.map&request=GetMetadata&layer=sand_0-5cm_mean
>   - Silt 0-5cm mean (g/kg): source-reported raw value 291. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fsilt.map&request=GetMetadata&layer=silt_0-5cm_mean
>   - Decision boundary: these are static gridded predictors at a documented representative cell, not a field soil test, current moisture measurement, or plant-available farm N/P/K result.
>   - Source: ISRIC SoilGrids static 0–5 cm profile — SOILGRIDS.
>   - Source location: public_worldcover_cropland_documented_representative_cell.
>   - Source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fphh2o.map&request=GetMetadata&layer=phh2o_0-5cm_mean
> **Historical Sentinel-2 / NDVI context (representative cell)**
>   - Scene: S2C_MSIL2A_20260305T045701_R119_T44PLT_20260305T092908 acquired 2026-03-05T04:57:01.025000Z; pixel class 4 (vegetation); quality clear_surface_pixel.
>   - Scene values: red DN 1308; NIR DN 7699; NDVI 0.709559.
>   - Pre-decision chronology: 4 clear observations from 2026-01-04T05:02:21.025000Z to 2026-03-30T04:56:59.024000Z (84.996 days); first/last NDVI 0.117341/0.155744; change 0.038403; slope 0.00248855 per day; recorded trend change_within_plus_or_minus_0_05_ndvi.
>   - Source record: Microsoft_Planetary_Computer_STAC; sentinel-2-l2a.
>   - Scope: NDVI is calculated as (B08 - B04) / (B08 + B04) from the exact selected Sentinel-2 L2A scene at the documented representative cropland coordinate.
>   - Decision boundary: this is not evidence of crop identity, field condition, crop stage, disease, nutrient status, or irrigation need.
>   - Source: Sentinel-2 L2A representative-cell context — SENTINEL2_L2A.
>   - Source location: S2C_MSIL2A_20260305T045701_R119_T44PLT_20260305T092908.
>   - Source URL: https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a/items/S2C_MSIL2A_20260305T045701_R119_T44PLT_20260305T092908
> **Historical nearest-mandi market context**
>   - Source-recorded decision-month mean: 1763.070.
>   - Comparison status: no_source_comparator; price-unit status as_reported_by_agmarknet_monthly_API_no_unit_inference; source commodity Maize in Ariyalur, Tamil Nadu.
>   - No historical price comparison is issued: the exact frozen official report has no prior-month or same-month-prior-year price to compare
>   - Decision boundary: the retained report does not support a current quotation, price forecast, sell/hold instruction, or farm-specific marketing decision.
>   - Source: Agmarknet historical monthly report context — AGMARKNET_MONTHLY_REPORT.
>   - Source location: decision date 2026-03-31.
>   - Source URL: https://api.agmarknet.gov.in/v1/price-trend/wholesale-prices-monthly?report_mode=Marketwise&commodity=4&year=2026&month=3&state=31&district=527
> Direct irrigation, farm-specific fertilizer, and treatment decisions remain gated by missing field evidence.
> Evidence trace: AGMARKNET_MONTHLY_REPORT, CIBRC_INSECTICIDE_2026, FROZEN_SCENARIO_MANIFEST, ICAR_CRIDA_CCP, ICAR_CRIDA_TN_ARIYALUR_CROP_PROFILE, ICAR_CRIDA_TN_ARIYALUR_SOWING_WINDOW, ICAR_RABI_STATE_ADVISORIES_2021_22, MAS_ENRICHMENT_CONTRACT.

## Chickpea — Beed, Maharashtra (2026-03-31)

- Scenario: `ANCHOR_PF_MH_BEED_CHICKPEA_RABI_20260331`
- Decision status: `conditional_operation_pending_field_precondition`
- Direct farm action: `False`
- Source IDs in decision trace: AGMARKNET_MONTHLY_REPORT, CIBRC_INSECTICIDE_2026, FROZEN_SCENARIO_MANIFEST, ICAR_CRIDA_CCP, ICAR_CRIDA_MH_BEED_CROP_PROFILE, ICAR_CRIDA_MH_BEED_SOWING_WINDOW, ICAR_RABI_STATE_ADVISORIES_2021_22, MAS_ENRICHMENT_CONTRACT, MPKV_KRISHI_DARSHANI_2023, NASA_POWER_HISTORICAL_WINDOW, NATURAL_SIGNAL_DIVERGENCE, SENTINEL2_L2A, SOILGRIDS, WDRA_REGISTERED_WAREHOUSES_MAHARASHTRA
- E0/E1 citation set unchanged: `True`; message exact match: `False`.

**Saved E1 farmer-facing plan**

> Scenario: Chickpea in Beed, Maharashtra (2026-03-31).
> **Regional seasonal planning window**
>   - Regional guidance: The declared rabi window for this crop and district is Oct-Mar; the scenario date falls in the late part of that window.
>   - Required scope or condition: The position is derived only from the declared district-scale season window and decision month. It is not an observed sowing date or field phenology stage.
>   - Not established by this scenario: actual_crop_stage_not_observed.
>   - Planning status: regional_planning_context_not_observed_field_stage.
>   - Source: District crop profile and sowing-window evidence — ICAR_CRIDA_CCP — ICAR-CRIDA.
>   - Source location: District CCP crop profile and sowing-window PDFs.
>   - Source URL: https://icar-crida.res.in/CCP/MH/Beed/1.7.pdf;https://icar-crida.res.in/CCP/MH/Beed/1.12.pdf
> Source-scoped regional operation: Post-harvest plan — Harvest Readiness: Harvest and thresh chickpea only after pods are hard; do not harvest while the crop is wet. It is not issued as a farm action; apply it only when its documented field condition is observed. Required condition: Only when hard pods and crop dryness are actually observed. Source: MPKV_KRISHI_DARSHANI_2023.
> **Conditional official operation — Official conditional operation**
>   - Regional guidance: Harvest and thresh chickpea only after pods are hard; do not harvest while the crop is wet.
>   - Method: Harvest only after the documented hard-pod maturity condition is observed.
>   - Required scope or condition: Only when chickpea maturity/hard pods and crop dryness are actually observed.
>   - Not established by this scenario: actual_crop_stage;documented_field_condition.
>   - Current status: not issued as a farm action; it remains conditional until the required condition is observed.
>   - Source wording: हरभरा पीक ११० ते १२० दिवसांमध्ये तयार होते. पीक ओलसर असताना काढणी करू नये. घाटे कडक झाल्यानंतर मग हरभऱ्याची काढणी करून मळणी करावी.
>   - Source: Krishi Darshani 2023 — MPKV_KRISHI_DARSHANI_2023 — Mahatma Phule Krishi Vidyapeeth, Rahuri.
>   - Source location: pdf_page_90_visual_operation_transcription.
>   - Source URL: https://mpkv.ac.in/Uploads/Publication/Krishi%20Darshani%20%202023_20230607043125.pdf
> **Regional nutrient planning reference**
>   - Regional guidance: Use the cited Maharashtra chickpea regional fertilizer source as a planning reference. The system preserves the documented scope and does not convert it into a farm-specific prescription or treatment order.
>   - Source-recorded regional schedule: For Maharashtra chickpea, the source records N:P2O5:K2O = 25:50:25 kg/ha as basal at sowing. It differentiates rainfed and irrigated sowing windows and seed-rate branches by desi or Kabuli type.
>   - Source-recorded applicability: This scenario does not record sowing, desi/Kabuli type, water regime, field soil test, secondary/micronutrient status or actual crop stage.
>   - Safety boundary: This is a source-recorded regional basal reference, not an individual field dose.
>   - Required scope or condition: Regional fallback only; pheromone-trap and NSKE prerequisites remain part of the source IPM bundle.
>   - Not established by this scenario: actual_crop_stage_and_field_soil_test_not_observed.
>   - Safety boundary: This remains a regional policy reference; no field-specific dose is issued.
>   - Source: ICAR Rabi Agro-Advisory for Farmers 2021–22 — ICAR_RABI_STATE_ADVISORIES_2021_22 — Indian Council of Agricultural Research.
>   - Source location: PDF p. 315 Maharashtra chickpea basal NPK.
>   - Source URL: https://icar.org.in/sites/default/files/2022-09/Rabi-Agro-Advisory-2021-22_0.pdf
> **Regional IPM planning reference**
>   - Regional guidance: Use the cited Maharashtra chickpea regional protection source as a planning reference. The system preserves the documented scope and does not convert it into a farm-specific prescription or treatment order.
>   - Source-recorded IPM method/options: For Helicoverpa/pod borer at the documented economic threshold, the source requires pheromone traps and an NSKE spray before recording a chemical option. It records quinalphos 25% EC at 20 mL/10 L water as an ETL-based option; the aligned PPQS record lists Bengal gram pod borer for quinalphos 25% EC at 1,000 mL/ha in 500-1,000 L water.
>   - Source-recorded applicability: No dated pod-borer diagnosis, economic-threshold observation, trap result, NSKE prerequisite, crop stage or field condition is recorded by this scenario.
>   - Safety boundary: This is source-recorded conditional IPM context, not a pesticide order.
>   - Source-recorded detail location: PDF p. 315 Maharashtra chickpea IPM.
>   - Required scope or condition: Regional fallback only; pheromone-trap and NSKE prerequisites remain part of the source IPM bundle.
>   - Not established by this scenario: dated_diagnosis_or_threshold_event_not_observed.
>   - Planning status: conditional_IPM_policy_only_diagnosis_or_threshold_event_required.
>   - Source: ICAR Rabi Agro-Advisory for Farmers 2021–22 — ICAR_RABI_STATE_ADVISORIES_2021_22 — Indian Council of Agricultural Research.
>   - Source location: PDF p. 315 ETL-based pod-borer IPM option.
>   - Source URL: https://icar.org.in/sites/default/files/2022-09/Rabi-Agro-Advisory-2021-22_0.pdf
> **Post-harvest plan — Harvest Readiness**
>   - Operation: Harvest and thresh chickpea only after pods are hard; do not harvest while the crop is wet.
>   - Required lot/harvest condition: Only when hard pods and crop dryness are actually observed.
>   - Not established by this scenario: actual_pod_hardness_and_crop_dryness_not_observed.
>   - Current status: conditional planning reference, not a harvest, storage, transport, or dispatch instruction.
>   - Source wording: हरभरा पीक ११० ते १२० दिवसांमध्ये तयार होते. पीक ओलसर असताना काढणी करू नये. घाटे कडक झाल्यानंतर मग हरभऱ्याची काढणी करून मळणी करावी.
>   - Source: Krishi Darshani 2023 — MPKV_KRISHI_DARSHANI_2023.
>   - Source location: pdf_page_90_visual_operation_transcription.
>   - Source URL: https://mpkv.ac.in/Uploads/Publication/Krishi%20Darshani%20%202023_20230607043125.pdf
> **Storage/logistics context: source-linked facility and warehouse candidates**
>   - These are collection-date public-directory or mapped-project records, not a live availability, booking, commodity-acceptance, freight, or dispatch instruction.
>   1. **KESONA WAREHOUSING CORPORATION**
>      - Source record ID: WDRA_MAHARASHTRA_7079015.
>      - Record type: wdra_registered_warehouse_district_match.
>      - Recorded location: Beed, Maharashtra.
>      - Captured registry status: Inactive.
>      - Listed registry capacity: 17500 MT; this is not current vacant capacity.
>      - Record scope: Collection-date WDRA registration context; no facility coordinates are exposed by this public registry response.
>      - Not established: No claim of commodity acceptance, current or historical capacity, vacancy, booking, quality, transport, freight, or storage duration.
>      - Source: WDRA_REGISTERED_WAREHOUSES_MAHARASHTRA.
>      - Source URL: https://wdra.gov.in/registered-wh-public
>   2. **Parli Tokwadi**
>      - Source record ID: WDRA_MAHARASHTRA_6575013.
>      - Record type: wdra_registered_warehouse_district_match.
>      - Recorded location: Beed, Maharashtra.
>      - Captured registry status: Active.
>      - Listed registry capacity: 15378 MT; this is not current vacant capacity.
>      - Record scope: Collection-date WDRA registration context; no facility coordinates are exposed by this public registry response.
>      - Not established: No claim of commodity acceptance, current or historical capacity, vacancy, booking, quality, transport, freight, or storage duration.
>      - Source: WDRA_REGISTERED_WAREHOUSES_MAHARASHTRA.
>      - Source URL: https://wdra.gov.in/registered-wh-public
>   3. **Kirti Oil Industries Pvt Ltd**
>      - Source record ID: WDRA_MAHARASHTRA_7099351.
>      - Record type: wdra_registered_warehouse_district_match.
>      - Recorded location: Beed, Maharashtra.
>      - Captured registry status: Inactive.
>      - Listed registry capacity: 13914 MT; this is not current vacant capacity.
>      - Record scope: Collection-date WDRA registration context; no facility coordinates are exposed by this public registry response.
>      - Not established: No claim of commodity acceptance, current or historical capacity, vacancy, booking, quality, transport, freight, or storage duration.
>      - Source: WDRA_REGISTERED_WAREHOUSES_MAHARASHTRA.
>      - Source URL: https://wdra.gov.in/registered-wh-public
> **Historical weather and water context**
>   - Historical decision window: 2026-03-01T00:00:00Z/2026-03-31T23:59:59Z; source-observed days: 31.
>   - Air context: mean temperature 29.239 °C; relative humidity 24.994%; wind speed 2.079 m/s; shortwave radiation 22.846 MJ/m²/day.
>   - Water context: precipitation 7.320 mm; modelled root-zone wetness mean/min/max 0.590/0.590/0.600; modelled top-layer wetness mean 0.187.
>   - Water-balance context: land evaporation 3.950 mm; precipitation minus land evaporation 3.370 mm.
>   - Scope: NASA POWER AG retrospective representative-cell context. GWETROOT/GWETTOP and EVLAND are source-modelled variables; precipitation minus land evaporation is an aggregated context indicator, not a field water balance, irrigation dose, or forecast.
>   - Decision boundary: this is retrospective representative-cell context, not current field moisture, an irrigation history, or a forecast.
>   - Source: NASA POWER historical weather and modelled water context — NASA_POWER_HISTORICAL_WINDOW.
>   - Source location: 2026-03-01T00:00:00Z/2026-03-31T23:59:59Z.
>   - Source URL: https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M%2CPRECTOTCORR%2CRH2M%2CWS2M&community=AG&longitude=75.782489&latitude=18.994057&start=20260301&end=20260331&format=JSON
> **Static SoilGrids context (representative cell, 0–5 cm)**
>   - Clay 0-5cm mean (g/kg): source-reported raw value 458. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fclay.map&request=GetMetadata&layer=clay_0-5cm_mean
>   - Nitrogen 0-5cm mean (cg/kg): source-reported raw value 143. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fnitrogen.map&request=GetMetadata&layer=nitrogen_0-5cm_mean
>   - Organic carbon density 0-5cm mean (hg/m3): source-reported raw value 188. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Focd.map&request=GetMetadata&layer=ocd_0-5cm_mean
>   - pH in H2O 0-5cm mean (pH*10): source-reported raw value 71. Metadata title states pH*10; raw_value_divided_by_10_is_pH.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fphh2o.map&request=GetMetadata&layer=phh2o_0-5cm_mean
>   - Sand 0-5cm mean (g/kg): source-reported raw value 289. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fsand.map&request=GetMetadata&layer=sand_0-5cm_mean
>   - Silt 0-5cm mean (g/kg): source-reported raw value 253. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fsilt.map&request=GetMetadata&layer=silt_0-5cm_mean
>   - Decision boundary: these are static gridded predictors at a documented representative cell, not a field soil test, current moisture measurement, or plant-available farm N/P/K result.
>   - Source: ISRIC SoilGrids static 0–5 cm profile — SOILGRIDS.
>   - Source location: public_worldcover_cropland_documented_representative_cell.
>   - Source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fphh2o.map&request=GetMetadata&layer=phh2o_0-5cm_mean
> **Historical Sentinel-2 / NDVI context (representative cell)**
>   - Scene: S2A_MSIL2A_20260306T053251_R062_T43QEB_20260306T103611 acquired 2026-03-06T05:32:51.024000Z; pixel class 5 (not_vegetated); quality clear_surface_pixel.
>   - Scene values: red DN 1874; NIR DN 2293; NDVI 0.100552.
>   - Pre-decision chronology: 4 clear observations from 2026-01-03T05:32:31.025000Z to 2026-03-29T05:26:39.024000Z (84.996 days); first/last NDVI 0.114591/0.022994; change -0.091597; slope -0.00078807 per day; recorded trend decrease_at_least_0_05_ndvi.
>   - Source record: Microsoft_Planetary_Computer_STAC; sentinel-2-l2a.
>   - Scope: NDVI is calculated as (B08 - B04) / (B08 + B04) from the exact selected Sentinel-2 L2A scene at the documented representative cropland coordinate.
>   - Decision boundary: this is not evidence of crop identity, field condition, crop stage, disease, nutrient status, or irrigation need.
>   - Source: Sentinel-2 L2A representative-cell context — SENTINEL2_L2A.
>   - Source location: S2A_MSIL2A_20260306T053251_R062_T43QEB_20260306T103611.
>   - Source URL: https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a/items/S2A_MSIL2A_20260306T053251_R062_T43QEB_20260306T103611
> **Historical nearest-mandi market context**
>   - Exact report values: decision-month mean 4983.007; prior-month mean 5073.187 (-1.778% change); same-month prior-year mean 5275.010 (-5.536% change).
>   - Report availability: prior_month_and_same_month_prior_year; price-unit status as_reported_by_agmarknet_monthly_API_no_unit_inference; source commodity Bengal Gram(Gram)(Whole) in Beed, Maharashtra.
>   - Scope: Means and percentage changes use price columns published in the exact frozen official monthly report. They are retrospective context, not a price forecast or sell/hold instruction.
>   - Decision boundary: the official monthly report supports historical comparison only; it contains no crop quality, storage cost, quantity, or forecast
>   - Source: Agmarknet historical monthly report context — AGMARKNET_MONTHLY_REPORT.
>   - Source location: decision date 2026-03-31.
>   - Source URL: https://api.agmarknet.gov.in/v1/price-trend/wholesale-prices-monthly?report_mode=Marketwise&commodity=6&year=2026&month=3&state=20&district=342
> **Evidence-resolution note**
>   - Historical NDVI and weather context diverged. Both remain context only, so the regional plan and action boundary were unchanged.
>      - Supporting source IDs: NASA_POWER_HISTORICAL_WINDOW, SENTINEL2_L2A.
>   - The full accepted/rejected evidence path remains in the technical trace; this note reports only the farmer-relevant conclusion.
> Direct irrigation, farm-specific fertilizer, and treatment decisions remain gated by missing field evidence.
> Evidence trace: AGMARKNET_MONTHLY_REPORT, CIBRC_INSECTICIDE_2026, FROZEN_SCENARIO_MANIFEST, ICAR_CRIDA_CCP, ICAR_CRIDA_MH_BEED_CROP_PROFILE, ICAR_CRIDA_MH_BEED_SOWING_WINDOW, ICAR_RABI_STATE_ADVISORIES_2021_22, MAS_ENRICHMENT_CONTRACT.

## Soybean — Dewas, Madhya Pradesh (2025-10-31)

- Scenario: `ANCHOR_PF_MP_DEWAS_SOYBEAN_KHARIF_20251031`
- Decision status: `conditional_operation_pending_field_precondition`
- Direct farm action: `False`
- Source IDs in decision trace: AGMARKNET_MONTHLY_REPORT, CIBRC_INSECTICIDE_2026, FROZEN_SCENARIO_MANIFEST, ICAR_CRIDA_CCP, ICAR_IISR_SOYBEAN_BULLETIN_2023, ICAR_IISR_SOYBEAN_CENTRAL_ADVISORY_2024, ICAR_IISR_WEEKLY_SOYBEAN_20230925, MAS_ENRICHMENT_CONTRACT, NASA_POWER_HISTORICAL_WINDOW, NATURAL_SIGNAL_DIVERGENCE, SENTINEL2_L2A, SOILGRIDS, WDRA_REGISTERED_WAREHOUSES_MADHYA_PRADESH
- E0/E1 citation set unchanged: `True`; message exact match: `False`.

**Saved E1 farmer-facing plan**

> Scenario: Soybean in Dewas, Madhya Pradesh (2025-10-31).
> **Regional seasonal planning window**
>   - Regional guidance: The declared kharif window for this crop and district is Jun-Oct; the scenario date falls in the late part of that window.
>   - Required scope or condition: The position is derived only from the declared district-scale season window and decision month. It is not an observed sowing date or field phenology stage.
>   - Not established by this scenario: actual_crop_stage_not_observed.
>   - Planning status: regional_planning_context_not_observed_field_stage.
>   - Source: District crop profile and sowing-window evidence — ICAR_CRIDA_CCP — ICAR-CRIDA.
>   - Source location: District CCP crop profile and sowing-window PDFs.
>   - Source URL: https://icar-crida.res.in/CCP/MP/Dewas/1.7.pdf;https://icar-crida.res.in/CCP/MP/Dewas/1.12.pdf
> Source-scoped regional operation: Post-harvest plan — Harvest Readiness: Harvest soybean when 90% of pods have changed colour to yellow. It is not issued as a farm action; apply it only when its documented field condition is observed. Required condition: Only when the 90% yellow-pod maturity condition is actually observed. Source: ICAR_IISR_SOYBEAN_BULLETIN_2023.
> **Conditional official operation — Official conditional operation**
>   - Regional guidance: Use fertilizer only as basal application; do not use fertilizer in a standing crop unless recommended by scientists.
>   - Method: Basal application at sowing.
>   - Source-recorded schedule/dose: No farm-specific dose; the source says the dose should be tailored after soil testing.
>   - Required scope or condition: Only at sowing and only as a regional baseline; a personalised dose requires a soil test.
>   - Not established by this scenario: actual_crop_stage;soil_test_for_personalised_dose.
>   - Current status: not issued as a farm action; it remains conditional until the required condition is observed.
>   - Source wording: In soybean, use of fertilizers is recommended only as basal application. Therefore, farmers are advised not to use any fertilizers in standing crop unless being recommended by the scientists.
>   - Source: Improved Technologies and Recommendations for Maximizing Soybean Productivity — ICAR_IISR_SOYBEAN_BULLETIN_2023 — ICAR–Indian Institute of Soybean Research.
>   - Source location: pdf_page_28.
>   - Source URL: https://icar-nsri.res.in/pdfdoc/ExtensionBulletin2023E_2.pdf
> **Conditional official operation — Official conditional operation**
>   - Regional guidance: Harvest when 90% of pods change colour to yellow.
>   - Required scope or condition: Only when 90% yellow-pod maturity is observed.
>   - Not established by this scenario: actual_crop_stage.
>   - Current status: not issued as a farm action; it remains conditional until the required condition is observed.
>   - Source wording: When 90% of the pods changes its color to yellow, it is the right indication to go for harvesting.
>   - Source: Improved Technologies and Recommendations for Maximizing Soybean Productivity — ICAR_IISR_SOYBEAN_BULLETIN_2023 — ICAR–Indian Institute of Soybean Research.
>   - Source location: pdf_page_33.
>   - Source URL: https://icar-nsri.res.in/pdfdoc/ExtensionBulletin2023E_2.pdf
> **Conditional official operation — Official conditional operation**
>   - Regional guidance: Thresh soybean at 350–400 rpm.
>   - Source-recorded schedule/dose: 350–400 rpm.
>   - Required scope or condition: Only after soybean has been harvested and threshing is being performed.
>   - Not established by this scenario: actual_crop_stage.
>   - Current status: not issued as a farm action; it remains conditional until the required condition is observed.
>   - Source wording: To maintain viability of seed and to avoid loss/mechanical damage, threshing should be done at 350-400 rpm.
>   - Source: Improved Technologies and Recommendations for Maximizing Soybean Productivity — ICAR_IISR_SOYBEAN_BULLETIN_2023 — ICAR–Indian Institute of Soybean Research.
>   - Source location: pdf_page_33.
>   - Source URL: https://icar-nsri.res.in/pdfdoc/ExtensionBulletin2023E_2.pdf
> **Regional nutrient planning reference**
>   - Regional guidance: Use the cited Madhya Pradesh soybean regional fertilizer source as a planning reference. The system preserves the documented scope and does not convert it into a farm-specific prescription or treatment order.
>   - Source-recorded regional schedule: For ICAR-IISR Central Zone soybean, the source records N:P2O5:K2O:S = 25:60:40:20 kg/ha, all at sowing. It lists source combinations of 56 kg urea plus 375-400 kg SSP plus 67 kg MOP; or 140 kg DAP plus 67 kg MOP plus 25 kg bentonite sulphur; or 200 kg 12:32:16 plus 25 kg bentonite sulphur per hectare. It specifies a seed-cum-fertilizer drill or broadcasting before sowing and says not to mix fertilizer with seed.
>   - Source-recorded applicability: Only the documented Central Zone states are in scope. Actual sowing, soil test, soil sulphur status, fertilizer availability, crop stage and prior application are not recorded.
>   - Safety boundary: This is a source-recorded regional sowing reference, not an individual field dose.
>   - Required scope or condition: Only ICAR-IISR Central Zone sites; use source ETLs and do not replace a field soil test.
>   - Not established by this scenario: actual_crop_stage_and_field_soil_test_not_observed.
>   - Safety boundary: This remains a regional policy reference; no field-specific dose is issued.
>   - Source: ICAR-IISR weekly advisory for soybean farmers, 1–7 July 2024 — ICAR_IISR_SOYBEAN_CENTRAL_ADVISORY_2024 — ICAR–Indian Institute of Soybean Research.
>   - Source location: PDF p. 2 central-zone NPKS at sowing.
>   - Source URL: https://icar-nsri.res.in/pdfdoc/Advisory2024/July,1-7th,2024.pdf
> **Regional IPM planning reference**
>   - Regional guidance: Use the cited Madhya Pradesh soybean regional protection source as a planning reference. The system preserves the documented scope and does not convert it into a farm-specific prescription or treatment order.
>   - Source-recorded IPM method/options: For soybean defoliators, the source records economic thresholds of green semilooper at 4 larvae/m row at flowering or 3 larvae/m at podding, and tobacco caterpillar at 10 larvae/m before flowering. It records chlorantraniliprole 18.5% SC at 150 mL/ha for these source-defined defoliator cases; the aligned PPQS record lists the same formulation for soybean green semilooper and tobacco caterpillar at 150 mL/ha.
>   - Source-recorded applicability: No dated pest diagnosis, species confirmation, larval count, crop stage, threshold event or field condition is recorded by this scenario.
>   - Safety boundary: This is source-recorded conditional IPM context, not an insecticide order.
>   - Required scope or condition: Only ICAR-IISR Central Zone sites; use source ETLs and do not replace a field soil test.
>   - Not established by this scenario: dated_diagnosis_or_threshold_event_not_observed.
>   - Planning status: conditional_IPM_policy_only_diagnosis_or_threshold_event_required.
>   - Source: Improved Technologies and Recommendations for Maximizing Soybean Productivity — ICAR_IISR_SOYBEAN_BULLETIN_2023 — ICAR–Indian Institute of Soybean Research.
>   - Source location: PDF pp. 47 and 49 ETL-based defoliator option.
>   - Source URL: https://icar-nsri.res.in/pdfdoc/ExtensionBulletin2023E_2.pdf
> **Post-harvest plan — Harvest Readiness**
>   - Operation: Harvest soybean when 90% of pods have changed colour to yellow.
>   - Required lot/harvest condition: Only when the 90% yellow-pod maturity condition is actually observed.
>   - Not established by this scenario: actual_pod_maturity_not_observed.
>   - Current status: conditional planning reference, not a harvest, storage, transport, or dispatch instruction.
>   - Source wording: When 90% of the pods changes its color to yellow, it is the right indication to go for harvesting.
>   - Source: Improved Technologies and Recommendations for Maximizing Soybean Productivity — ICAR_IISR_SOYBEAN_BULLETIN_2023.
>   - Source location: pdf_page_33.
>   - Source URL: https://icar-nsri.res.in/pdfdoc/ExtensionBulletin2023E_2.pdf
> **Post-harvest plan — Threshing**
>   - Operation: Use the cited threshing speed to reduce mechanical damage when threshing soybean.
>   - Method or parameter: 350–400 rpm.
>   - Required lot/harvest condition: Only after harvest and when the actual threshing system is known.
>   - Not established by this scenario: actual_harvest_status_and_thresher_configuration_not_observed.
>   - Current status: conditional planning reference, not a harvest, storage, transport, or dispatch instruction.
>   - Source wording: To maintain viability of seed and to avoid loss/mechanical damage, threshing should be done at 350-400 rpm.
>   - Source: Improved Technologies and Recommendations for Maximizing Soybean Productivity — ICAR_IISR_SOYBEAN_BULLETIN_2023.
>   - Source location: pdf_page_33.
>   - Source URL: https://icar-nsri.res.in/pdfdoc/ExtensionBulletin2023E_2.pdf
> **Post-harvest plan — Dry Storage**
>   - Operation: Sun-dry harvested soybean before threshing; if threshing is delayed, protect it from rain.
>   - Required lot/harvest condition: Only after actual harvest and with documented drying/storage conditions.
>   - Not established by this scenario: actual_harvest_status_drying_condition_and_storage_condition_not_observed.
>   - Current status: conditional planning reference, not a harvest, storage, transport, or dispatch instruction.
>   - Source wording: The harvested crop must be threshed after sun drying. If the threshing is to be done later, it should be stored at safe place protecting from rains.
>   - Source: ICAR-IISR weekly soybean advisory, 25 Sep–01 Oct 2023 — ICAR_IISR_WEEKLY_SOYBEAN_20230925.
>   - Source location: pdf_page_1.
>   - Source URL: https://icar-nsri.res.in/pdfdoc/Advisory2023/25%20Sept-1Oct%202023.pdf
> **Storage/logistics context: source-linked facility and warehouse candidates**
>   - These are collection-date public-directory or mapped-project records, not a live availability, booking, commodity-acceptance, freight, or dispatch instruction.
>   1. **Shree Subham Logistics - Dewas**
>      - Source record ID: WDRA_MADHYA_PRADESH_1001866.
>      - Record type: wdra_registered_warehouse_district_match.
>      - Recorded location: Dewas, Madhya Pradesh.
>      - Captured registry status: Active.
>      - Listed registry capacity: 35135 MT; this is not current vacant capacity.
>      - Record scope: Collection-date WDRA registration context; no facility coordinates are exposed by this public registry response.
>      - Not established: No claim of commodity acceptance, current or historical capacity, vacancy, booking, quality, transport, freight, or storage duration.
>      - Source: WDRA_REGISTERED_WAREHOUSES_MADHYA_PRADESH.
>      - Source URL: https://wdra.gov.in/registered-wh-public
>   2. **MPWLC Siya Dewas**
>      - Source record ID: WDRA_MADHYA_PRADESH_7159569.
>      - Record type: wdra_registered_warehouse_district_match.
>      - Recorded location: Dewas, Madhya Pradesh.
>      - Captured registry status: Inactive.
>      - Listed registry capacity: 21926 MT; this is not current vacant capacity.
>      - Record scope: Collection-date WDRA registration context; no facility coordinates are exposed by this public registry response.
>      - Not established: No claim of commodity acceptance, current or historical capacity, vacancy, booking, quality, transport, freight, or storage duration.
>      - Source: WDRA_REGISTERED_WAREHOUSES_MADHYA_PRADESH.
>      - Source URL: https://wdra.gov.in/registered-wh-public
>   3. **dewas ware housing jamgod**
>      - Source record ID: WDRA_MADHYA_PRADESH_6940050.
>      - Record type: wdra_registered_warehouse_district_match.
>      - Recorded location: Dewas, Madhya Pradesh.
>      - Captured registry status: Inactive.
>      - Listed registry capacity: 17588 MT; this is not current vacant capacity.
>      - Record scope: Collection-date WDRA registration context; no facility coordinates are exposed by this public registry response.
>      - Not established: No claim of commodity acceptance, current or historical capacity, vacancy, booking, quality, transport, freight, or storage duration.
>      - Source: WDRA_REGISTERED_WAREHOUSES_MADHYA_PRADESH.
>      - Source URL: https://wdra.gov.in/registered-wh-public
> **Historical weather and water context**
>   - Historical decision window: 2025-10-01T00:00:00Z/2025-10-31T23:59:59Z; source-observed days: 31.
>   - Air context: mean temperature 23.145 °C; relative humidity 81.523%; wind speed 1.748 m/s; shortwave radiation 15.731 MJ/m²/day.
>   - Water context: precipitation 64.000 mm; modelled root-zone wetness mean/min/max 0.853/0.800/0.910; modelled top-layer wetness mean 0.856.
>   - Water-balance context: land evaporation 129.450 mm; precipitation minus land evaporation -65.450 mm.
>   - Scope: NASA POWER AG retrospective representative-cell context. GWETROOT/GWETTOP and EVLAND are source-modelled variables; precipitation minus land evaporation is an aggregated context indicator, not a field water balance, irrigation dose, or forecast.
>   - Decision boundary: this is retrospective representative-cell context, not current field moisture, an irrigation history, or a forecast.
>   - Source: NASA POWER historical weather and modelled water context — NASA_POWER_HISTORICAL_WINDOW.
>   - Source location: 2025-10-01T00:00:00Z/2025-10-31T23:59:59Z.
>   - Source URL: https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M%2CPRECTOTCORR%2CRH2M%2CWS2M&community=AG&longitude=76.532632&latitude=22.790539&start=20251001&end=20251031&format=JSON
> **Static SoilGrids context (representative cell, 0–5 cm)**
>   - Clay 0-5cm mean (g/kg): source-reported raw value 402. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fclay.map&request=GetMetadata&layer=clay_0-5cm_mean
>   - Nitrogen 0-5cm mean (cg/kg): source-reported raw value 148. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fnitrogen.map&request=GetMetadata&layer=nitrogen_0-5cm_mean
>   - Organic carbon density 0-5cm mean (hg/m3): source-reported raw value 205. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Focd.map&request=GetMetadata&layer=ocd_0-5cm_mean
>   - pH in H2O 0-5cm mean (pH*10): source-reported raw value 73. Metadata title states pH*10; raw_value_divided_by_10_is_pH.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fphh2o.map&request=GetMetadata&layer=phh2o_0-5cm_mean
>   - Sand 0-5cm mean (g/kg): source-reported raw value 170. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fsand.map&request=GetMetadata&layer=sand_0-5cm_mean
>   - Silt 0-5cm mean (g/kg): source-reported raw value 428. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fsilt.map&request=GetMetadata&layer=silt_0-5cm_mean
>   - Decision boundary: these are static gridded predictors at a documented representative cell, not a field soil test, current moisture measurement, or plant-available farm N/P/K result.
>   - Source: ISRIC SoilGrids static 0–5 cm profile — SOILGRIDS.
>   - Source location: public_worldcover_cropland_documented_representative_cell.
>   - Source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fphh2o.map&request=GetMetadata&layer=phh2o_0-5cm_mean
> **Historical Sentinel-2 / NDVI context (representative cell)**
>   - Scene: S2B_MSIL2A_20251010T052649_R105_T43QFF_20251010T075840 acquired 2025-10-10T05:26:49.024000Z; pixel class 4 (vegetation); quality clear_surface_pixel.
>   - Scene values: red DN 1781; NIR DN 3962; NDVI 0.379767.
>   - Pre-decision chronology: 4 clear observations from 2025-08-06T05:27:01.024000Z to 2025-10-20T05:27:49.024000Z (75.001 days); first/last NDVI 0.556757/0.242318; change -0.314439; slope -0.00385187 per day; recorded trend decrease_at_least_0_05_ndvi.
>   - Source record: Microsoft_Planetary_Computer_STAC; sentinel-2-l2a.
>   - Scope: NDVI is calculated as (B08 - B04) / (B08 + B04) from the exact selected Sentinel-2 L2A scene at the documented representative cropland coordinate.
>   - Decision boundary: this is not evidence of crop identity, field condition, crop stage, disease, nutrient status, or irrigation need.
>   - Source: Sentinel-2 L2A representative-cell context — SENTINEL2_L2A.
>   - Source location: S2B_MSIL2A_20251010T052649_R105_T43QFF_20251010T075840.
>   - Source URL: https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a/items/S2B_MSIL2A_20251010T052649_R105_T43QFF_20251010T075840
> **Historical nearest-mandi market context**
>   - Exact report values: decision-month mean 3818.503; prior-month mean 3801.273 (0.453% change); same-month prior-year mean 4094.603 (-6.743% change).
>   - Report availability: prior_month_and_same_month_prior_year; price-unit status as_reported_by_agmarknet_monthly_API_no_unit_inference; source commodity Soyabean in Dewas, Madhya Pradesh.
>   - Scope: Means and percentage changes use price columns published in the exact frozen official monthly report. They are retrospective context, not a price forecast or sell/hold instruction.
>   - Decision boundary: the official monthly report supports historical comparison only; it contains no crop quality, storage cost, quantity, or forecast
>   - Source: Agmarknet historical monthly report context — AGMARKNET_MONTHLY_REPORT.
>   - Source location: decision date 2025-10-31.
>   - Source URL: https://api.agmarknet.gov.in/v1/price-trend/wholesale-prices-monthly?report_mode=Marketwise&commodity=13&year=2025&month=10&state=19&district=301
> Direct irrigation, farm-specific fertilizer, and treatment decisions remain gated by missing field evidence.
> Evidence trace: AGMARKNET_MONTHLY_REPORT, CIBRC_INSECTICIDE_2026, FROZEN_SCENARIO_MANIFEST, ICAR_CRIDA_CCP, ICAR_IISR_SOYBEAN_BULLETIN_2023, ICAR_IISR_SOYBEAN_CENTRAL_ADVISORY_2024, ICAR_IISR_WEEKLY_SOYBEAN_20230925, MAS_ENRICHMENT_CONTRACT.

## Tomato — Coimbatore, Tamil Nadu (2025-12-31)

- Scenario: `ANCHOR_PF_TN_COIMBATORE_TOMATO_RABI_20251231`
- Decision status: `conditional_operation_pending_field_precondition`
- Direct farm action: `False`
- Source IDs in decision trace: AGMARKNET_MONTHLY_REPORT, CIBRC_FUNGICIDE_2026, FROZEN_SCENARIO_MANIFEST, ICAR_CRIDA_TN_COIMBATORE_CROP_PROFILE, ICAR_RABI_STATE_ADVISORIES_2021_22, MAS_ENRICHMENT_CONTRACT, NASA_POWER_HISTORICAL_WINDOW, NATURAL_SIGNAL_DIVERGENCE, NHB_ICAP_GEO_FACILITIES, SENTINEL2_L2A, SOILGRIDS, TNAU_TOMATO_EARLY_BLIGHT_2023, TNAU_TOMATO_FERTIGATION_2014, TNAU_TOMATO_FRUIT_BORER_2023, TNAU_TOMATO_POSTHARVEST_HARVESTING
- E0/E1 citation set unchanged: `True`; message exact match: `False`.

**Saved E1 farmer-facing plan**

> Scenario: Tomato in Coimbatore, Tamil Nadu (2025-12-31).
> **Regional seasonal planning window**
>   - Regional guidance: The declared rabi window for this crop and district is Oct-Mar; the scenario date falls in the middle part of that window.
>   - Required scope or condition: The position is derived only from the declared district-scale season window and decision month. It is not an observed sowing date or field phenology stage.
>   - Not established by this scenario: actual_crop_stage_not_observed.
>   - Planning status: regional_planning_context_not_observed_field_stage.
>   - Source: ICAR Rabi agro-advisory crop-season evidence — ICAR_RABI_STATE_ADVISORIES_2021_22 — Indian Council of Agricultural Research.
>   - Source location: PDF pp. 388 and 394-395 Tamil Nadu and Puducherry Rabi tomato chapter.
>   - Source URL: https://icar-crida.res.in/CCP/TN/Coimbatore/1.7.pdf;https://icar-crida.res.in/CCP/TN/Coimbatore/1.12.pdf
> Source-scoped regional operation: Post-harvest plan — Harvest Readiness: Match tomato harvest maturity to the intended market and transport distance. It is not issued as a farm action; apply it only when its documented field condition is observed. Required condition: Only after observing fruit maturity and knowing the intended market; neither is in the scenario. Source: TNAU_TOMATO_POSTHARVEST_HARVESTING.
> **Conditional official operation — Official conditional operation**
>   - Regional guidance: Use only the documented early-blight fungicide alternatives after a supported diagnosis.
>   - Method: Spray one of the source-listed formulations.
>   - Source-recorded schedule/dose: Iprodione 50% WP 600 g/ac; or Azoxystrobin 23% SC 200 ml/ac; or Mancozeb 35% SC 1 kg/ac.
>   - Required scope or condition: Only after a supported early-blight diagnosis and applicable labelled/regulatory verification.
>   - Not established by this scenario: actual_crop_stage;dated_diagnosis_or_threshold.
>   - Current status: not issued as a farm action; it remains conditional until the required condition is observed.
>   - Source wording: Spray Iprodione 50% WP @ 600 g/ac or Azoxystrobin 23% SC @ 200 ml/ac or Mancozeb 35% SC @ 1 kg/ac
>   - Source: TNAU Agritech tomato early-blight integrated disease management — TNAU_TOMATO_EARLY_BLIGHT_2023 — Tamil Nadu Agricultural University.
>   - Source location: html_document.
>   - Source URL: https://agritech.tnau.ac.in/crop_protection/tomato_diseases_2.html
> **Conditional official operation — Official conditional operation**
>   - Regional guidance: Remove and destroy crop debris.
>   - Required scope or condition: Only where relevant crop debris is present and this disease-management measure is applicable.
>   - Not established by this scenario: documented_field_condition.
>   - Current status: not issued as a farm action; it remains conditional until the required condition is observed.
>   - Source wording: Removal and destruction of crop debris.
>   - Source: TNAU Agritech tomato early-blight integrated disease management — TNAU_TOMATO_EARLY_BLIGHT_2023 — Tamil Nadu Agricultural University.
>   - Source location: html_document.
>   - Source URL: https://agritech.tnau.ac.in/crop_protection/tomato_diseases_2.html
> **Conditional official operation — Official conditional operation**
>   - Regional guidance: Set up Helilure pheromone traps.
>   - Source-recorded schedule/dose: 12 traps/ha.
>   - Required scope or condition: Only for an existing tomato crop when the implementation stage is documented.
>   - Not established by this scenario: actual_crop_stage.
>   - Current status: not issued as a farm action; it remains conditional until the required condition is observed.
>   - Source wording: Setup pheromone trap with Helilure at 12/ha
>   - Source: TNAU Agritech tomato fruit-borer integrated management — TNAU_TOMATO_FRUIT_BORER_2023 — Tamil Nadu Agricultural University.
>   - Source location: html_document.
>   - Source URL: https://agritech.tnau.ac.in/crop_protection/tomato/tomato_1.html
> **Conditional official operation — Official conditional operation**
>   - Regional guidance: Collect and destroy infected fruits and grown-up larvae.
>   - Required scope or condition: Only when fruit borer infestation/infected fruit is observed.
>   - Not established by this scenario: actual_crop_stage;dated_diagnosis_or_threshold.
>   - Current status: not issued as a farm action; it remains conditional until the required condition is observed.
>   - Source wording: Collect and destroy the infected fruits and grown up larvae
>   - Source: TNAU Agritech tomato fruit-borer integrated management — TNAU_TOMATO_FRUIT_BORER_2023 — Tamil Nadu Agricultural University.
>   - Source location: html_document.
>   - Source URL: https://agritech.tnau.ac.in/crop_protection/tomato/tomato_1.html
> **Conditional official operation — Official conditional operation**
>   - Regional guidance: Use the documented hybrid-tomato drip-fertigation schedule.
>   - Method: The source applies 75% of P as basal and the remaining nutrients through fertigation in stage-specific splits.
>   - Source-recorded schedule/dose: 200:250:250 kg NPK/ha for hybrids.
>   - Required scope or condition: Only for documented tomato hybrids under the documented drip-fertigation system and known crop stage.
>   - Not established by this scenario: actual_crop_stage;soil_test_for_personalised_dose;documented_system_or_variety.
>   - Current status: not issued as a farm action; it remains conditional until the required condition is observed.
>   - Source wording: The nutrient requirement for hybrids is 200:250:250 kg of NPK per ha.
>   - Source: TNAU tomato fertigation schedule for hybrids — TNAU_TOMATO_FERTIGATION_2014 — Tamil Nadu Agricultural University.
>   - Source location: pdf_page_1.
>   - Source URL: https://agritech.tnau.ac.in/horticulture/ferti_schedule.pdf
> **Regional nutrient planning reference**
>   - Regional guidance: Use the cited Tamil Nadu tomato regional fertilizer source as a planning reference. The system preserves the documented scope and does not convert it into a farm-specific prescription or treatment order.
>   - Source-recorded regional schedule: For hybrid tomato under the source's drip-fertigation system, total N:P2O5:K2O is 200:250:250 kg/ha. The source applies 75% P2O5 (187.5 kg/ha, stated as 1,172 kg superphosphate) as basal, then fertigates remaining N:P2O5:K2O = 200:62.5:250 kg/ha once every three days across transplanting-establishment (10 days), flower initiation-flowering (30 days), flowering-fruit set (30 days), and alternate days from picking (80 days).
>   - Source-recorded applicability: The scenario does not record hybrid status, drip-fertigation availability, actual transplanting date, crop stage, field soil test or previous application.
>   - Safety boundary: This is a source-recorded conditional regional schedule, not an individual field dose.
>   - Required scope or condition: Hybrid tomato under documented drip fertigation only; use the diagnosis-triggered early-blight bundle and not a routine spray.
>   - Not established by this scenario: actual_crop_stage_and_field_soil_test_not_observed.
>   - Safety boundary: This remains a regional policy reference; no field-specific dose is issued.
>   - Source: TNAU tomato fertigation schedule for hybrids — TNAU_TOMATO_FERTIGATION_2014 — Tamil Nadu Agricultural University.
>   - Source location: PDF p. 1 hybrid tomato drip-fertigation schedule.
>   - Source URL: https://agritech.tnau.ac.in/horticulture/ferti_schedule.pdf
> **Regional IPM planning reference**
>   - Regional guidance: Use the cited Tamil Nadu tomato regional protection source as a planning reference. The system preserves the documented scope and does not convert it into a farm-specific prescription or treatment order.
>   - Source-recorded IPM method/options: For confirmed tomato early blight, the source records crop-debris removal, rotation and seed treatment before listing a source option. It records azoxystrobin 18.2% plus difenoconazole 11.4% SC at 200 mL/acre; the aligned PPQS record lists the same formulation for tomato early and late blight.
>   - Source-recorded applicability: No dated early-blight diagnosis, disease severity, crop stage, field condition or label-use decision is recorded by this scenario.
>   - Safety boundary: This is source-recorded conditional IPM context, not a fungicide order.
>   - Required scope or condition: Hybrid tomato under documented drip fertigation only; use the diagnosis-triggered early-blight bundle and not a routine spray.
>   - Not established by this scenario: dated_diagnosis_or_threshold_event_not_observed.
>   - Planning status: conditional_IPM_policy_only_diagnosis_or_threshold_event_required.
>   - Source: TNAU Agritech tomato early-blight integrated disease management — TNAU_TOMATO_EARLY_BLIGHT_2023 — Tamil Nadu Agricultural University.
>   - Source location: HTML early-blight integrated management page.
>   - Source URL: https://agritech.tnau.ac.in/crop_protection/tomato_diseases_2.html
> **Post-harvest plan — Harvest Readiness**
>   - Operation: Match tomato harvest maturity to the intended market and transport distance.
>   - Method or parameter: The cited TNAU source distinguishes firm mature-green fruit for distant shipping from turning-pink/half-ripe fruit for fresh consumption.
>   - Required lot/harvest condition: Only after observing fruit maturity and knowing the intended market; neither is in the scenario.
>   - Not established by this scenario: actual_fruit_maturity_and_intended_market_not_observed.
>   - Current status: conditional planning reference, not a harvest, storage, transport, or dispatch instruction.
>   - Source wording: Generally, firm mature green fruits are best suited for shipping or distant marketing. For fresh consumption, tomatoes are harvested at the turning pink or half ripe stage.
>   - Source: TNAU tomato harvesting and post-harvest techniques — TNAU_TOMATO_POSTHARVEST_HARVESTING.
>   - Source location: html_paragraphs_171_to_173.
>   - Source URL: https://agritech.tnau.ac.in/org_farm/orgfarm_tomato_harvest.html
> **Post-harvest plan — Grading**
>   - Operation: Remove damaged, rotten, and cracked tomatoes before grading sound fruit.
>   - Required lot/harvest condition: Only after a harvested lot is available for physical inspection.
>   - Not established by this scenario: actual_harvested_lot_quality_not_observed.
>   - Current status: conditional planning reference, not a harvest, storage, transport, or dispatch instruction.
>   - Source wording: Damaged, rotten and cracked fruit are removed. Healthy, attractive, clean and bright fruits are preferred.
>   - Source: TNAU tomato harvesting and post-harvest techniques — TNAU_TOMATO_POSTHARVEST_HARVESTING.
>   - Source location: html_paragraph_176.
>   - Source URL: https://agritech.tnau.ac.in/org_farm/orgfarm_tomato_harvest.html
> **Post-harvest plan — Packing Transport**
>   - Operation: Use packing that protects tomatoes from crushing and permits air circulation.
>   - Method or parameter: The cited source describes plastic crates for local markets and rigid packing that protects fruit while allowing circulation.
>   - Required lot/harvest condition: Only after lot grade, destination, pack format, and transport arrangement are known.
>   - Not established by this scenario: actual_lot_grade_destination_packaging_and_transport_availability_not_observed.
>   - Current status: conditional planning reference, not a harvest, storage, transport, or dispatch instruction.
>   - Source wording: Plastic crates are more convenient for handling since they can be stacked one above the other. The contoured rim keeps the product safe and allows sufficient air circulation. The packing should be rigid enough to protect the fruits from being crushed.
>   - Source: TNAU tomato harvesting and post-harvest techniques — TNAU_TOMATO_POSTHARVEST_HARVESTING.
>   - Source location: html_paragraph_178.
>   - Source URL: https://agritech.tnau.ac.in/org_farm/orgfarm_tomato_harvest.html
> **Post-harvest plan — Cold Chain**
>   - Operation: Use the cited storage-temperature guidance only after maturity and cold-chain feasibility are known.
>   - Method or parameter: The cited TNAU source gives 12–15°C as an ideal storage range and 13°C with 90–95% relative humidity to slow ripening.
>   - Required lot/harvest condition: Only for a harvested lot with observed maturity and verified facility temperature/humidity capability.
>   - Not established by this scenario: actual_fruit_maturity_and_verified_cold_chain_capability_not_observed.
>   - Current status: conditional planning reference, not a harvest, storage, transport, or dispatch instruction.
>   - Source wording: Temperature between 12–15 oC is ideal for storage. A temperature of 13 oC and 90–95% relative humidity is recommended to slow down ripening.
>   - Source: TNAU tomato harvesting and post-harvest techniques — TNAU_TOMATO_POSTHARVEST_HARVESTING.
>   - Source location: html_paragraph_180.
>   - Source URL: https://agritech.tnau.ac.in/org_farm/orgfarm_tomato_harvest.html
> **Storage/logistics context: source-linked facility and warehouse candidates**
>   - These are collection-date public-directory or mapped-project records, not a live availability, booking, commodity-acceptance, freight, or dispatch instruction.
>   1. **DANDU MARIAMAN DAIRY**
>      - Source record ID: NHB_ICAP_TAMIL_NADU_02402.
>      - Record type: nhb_mapped_project_proximity.
>      - Recorded location: Coimbatore, Tamil Nadu.
>      - Captured registry status: location_record_only.
>      - Captured straight-line distance: 21.96 km.
>      - Captured static road-geometry estimate: 29.50 km; 36.8 minutes. It is not live traffic or a dispatch estimate.
>      - Static-route source URL: https://router.project-osrm.org/route/v1/driving/76.977097,10.815941;76.940000,11.010000?overview=false&steps=false
>      - Record scope: Collection-date mapped-project context; geodesic distance is derived from public coordinates, not a road route or travel-time estimate.
>      - Not established: No claim that the project is a suitable cold-store, has a required temperature, accepts tomato, is operating, has capacity, can be booked, or was available on the scenario date.
>      - Source: NHB_ICAP_GEO_FACILITIES.
>      - Source URL: https://nhb.gov.in/Handlers/GeoIndiaHandlerGis.ashx
>   2. **KOLAR S KOLAR COLD STORAGE**
>      - Source record ID: NHB_ICAP_TAMIL_NADU_01474.
>      - Record type: nhb_mapped_project_proximity.
>      - Recorded location: Coimbatore, Tamil Nadu.
>      - Captured registry status: location_record_only.
>      - Captured straight-line distance: 51.61 km.
>      - Captured static road-geometry estimate: 66.88 km; 69.0 minutes. It is not live traffic or a dispatch estimate.
>      - Static-route source URL: https://router.project-osrm.org/route/v1/driving/76.977097,10.815941;76.970000,11.280000?overview=false&steps=false
>      - Record scope: Collection-date mapped-project context; geodesic distance is derived from public coordinates, not a road route or travel-time estimate.
>      - Not established: No claim that the project is a suitable cold-store, has a required temperature, accepts tomato, is operating, has capacity, can be booked, or was available on the scenario date.
>      - Source: NHB_ICAP_GEO_FACILITIES.
>      - Source URL: https://nhb.gov.in/Handlers/GeoIndiaHandlerGis.ashx
>   3. **SRI AYYAPPA HITECH COLD STORAGE**
>      - Source record ID: NHB_ICAP_TAMIL_NADU_02401.
>      - Record type: nhb_mapped_project_proximity.
>      - Recorded location: Coimbatore, Tamil Nadu.
>      - Captured registry status: location_record_only.
>      - Captured straight-line distance: 52.80 km.
>      - Captured static road-geometry estimate: 69.58 km; 71.4 minutes. It is not live traffic or a dispatch estimate.
>      - Static-route source URL: https://router.project-osrm.org/route/v1/driving/76.977097,10.815941;76.950000,11.290000?overview=false&steps=false
>      - Record scope: Collection-date mapped-project context; geodesic distance is derived from public coordinates, not a road route or travel-time estimate.
>      - Not established: No claim that the project is a suitable cold-store, has a required temperature, accepts tomato, is operating, has capacity, can be booked, or was available on the scenario date.
>      - Source: NHB_ICAP_GEO_FACILITIES.
>      - Source URL: https://nhb.gov.in/Handlers/GeoIndiaHandlerGis.ashx
> **Historical weather and water context**
>   - Historical decision window: 2025-12-01T00:00:00Z/2025-12-31T23:59:59Z; source-observed days: 31.
>   - Air context: mean temperature 21.664 °C; relative humidity 77.907%; wind speed 1.661 m/s; shortwave radiation 17.525 MJ/m²/day.
>   - Water context: precipitation 22.450 mm; modelled root-zone wetness mean/min/max 0.656/0.600/0.710; modelled top-layer wetness mean 0.633.
>   - Water-balance context: land evaporation 88.850 mm; precipitation minus land evaporation -66.400 mm.
>   - Scope: NASA POWER AG retrospective representative-cell context. GWETROOT/GWETTOP and EVLAND are source-modelled variables; precipitation minus land evaporation is an aggregated context indicator, not a field water balance, irrigation dose, or forecast.
>   - Decision boundary: this is retrospective representative-cell context, not current field moisture, an irrigation history, or a forecast.
>   - Source: NASA POWER historical weather and modelled water context — NASA_POWER_HISTORICAL_WINDOW.
>   - Source location: 2025-12-01T00:00:00Z/2025-12-31T23:59:59Z.
>   - Source URL: https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M%2CPRECTOTCORR%2CRH2M%2CWS2M&community=AG&longitude=76.977097&latitude=10.815941&start=20251201&end=20251231&format=JSON
> **Static SoilGrids context (representative cell, 0–5 cm)**
>   - Clay 0-5cm mean (g/kg): source-reported raw value 238. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fclay.map&request=GetMetadata&layer=clay_0-5cm_mean
>   - Nitrogen 0-5cm mean (cg/kg): source-reported raw value 210. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fnitrogen.map&request=GetMetadata&layer=nitrogen_0-5cm_mean
>   - Organic carbon density 0-5cm mean (hg/m3): source-reported raw value 242. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Focd.map&request=GetMetadata&layer=ocd_0-5cm_mean
>   - pH in H2O 0-5cm mean (pH*10): source-reported raw value 68. Metadata title states pH*10; raw_value_divided_by_10_is_pH.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fphh2o.map&request=GetMetadata&layer=phh2o_0-5cm_mean
>   - Sand 0-5cm mean (g/kg): source-reported raw value 528. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fsand.map&request=GetMetadata&layer=sand_0-5cm_mean
>   - Silt 0-5cm mean (g/kg): source-reported raw value 234. Raw value retained; use metadata title before any unit conversion.
>     - Property source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fsilt.map&request=GetMetadata&layer=silt_0-5cm_mean
>   - Decision boundary: these are static gridded predictors at a documented representative cell, not a field soil test, current moisture measurement, or plant-available farm N/P/K result.
>   - Source: ISRIC SoilGrids static 0–5 cm profile — SOILGRIDS.
>   - Source location: public_worldcover_cropland_documented_representative_cell.
>   - Source URL: https://maps.isric.org/mapserv?map=%2Fmap%2Fphh2o.map&request=GetMetadata&layer=phh2o_0-5cm_mean
> **Historical Sentinel-2 / NDVI context (representative cell)**
>   - Scene: S2C_MSIL2A_20251208T051221_R019_T43PGN_20251208T081319 acquired 2025-12-08T05:12:21.025000Z; pixel class 4 (vegetation); quality clear_surface_pixel.
>   - Scene values: red DN 1672; NIR DN 3517; NDVI 0.355560.
>   - Pre-decision chronology: 3 clear observations from 2025-10-29T05:10:41.025000Z to 2025-12-13T05:11:19.024000Z (45.000 days); first/last NDVI 0.390145/0.352041; change -0.038104; slope -0.00085360 per day; recorded trend change_within_plus_or_minus_0_05_ndvi.
>   - Source record: Microsoft_Planetary_Computer_STAC; sentinel-2-l2a.
>   - Scope: NDVI is calculated as (B08 - B04) / (B08 + B04) from the exact selected Sentinel-2 L2A scene at the documented representative cropland coordinate.
>   - Decision boundary: this is not evidence of crop identity, field condition, crop stage, disease, nutrient status, or irrigation need.
>   - Source: Sentinel-2 L2A representative-cell context — SENTINEL2_L2A.
>   - Source location: S2C_MSIL2A_20251208T051221_R019_T43PGN_20251208T081319.
>   - Source URL: https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a/items/S2C_MSIL2A_20251208T051221_R019_T43PGN_20251208T081319
> **Historical nearest-mandi market context**
>   - Exact report values: decision-month mean 4826.805; prior-month mean 3618.450 (33.394% change); same-month prior-year mean 2995.399 (61.141% change).
>   - Report availability: prior_month_and_same_month_prior_year; price-unit status as_reported_by_agmarknet_monthly_API_no_unit_inference; source commodity Tomato in Coimbatore, Tamil Nadu.
>   - Scope: Means and percentage changes use price columns published in the exact frozen official monthly report. They are retrospective context, not a price forecast or sell/hold instruction.
>   - Decision boundary: the official monthly report supports historical comparison only; it contains no crop quality, storage cost, quantity, or forecast
>   - Source: Agmarknet historical monthly report context — AGMARKNET_MONTHLY_REPORT.
>   - Source location: decision date 2025-12-31.
>   - Source URL: https://api.agmarknet.gov.in/v1/price-trend/wholesale-prices-monthly?report_mode=Marketwise&commodity=65&year=2025&month=12&state=31&district=530
> Direct irrigation, farm-specific fertilizer, and treatment decisions remain gated by missing field evidence.
> Evidence trace: AGMARKNET_MONTHLY_REPORT, CIBRC_FUNGICIDE_2026, FROZEN_SCENARIO_MANIFEST, ICAR_CRIDA_TN_COIMBATORE_CROP_PROFILE, ICAR_RABI_STATE_ADVISORIES_2021_22, MAS_ENRICHMENT_CONTRACT, NASA_POWER_HISTORICAL_WINDOW, NATURAL_SIGNAL_DIVERGENCE.

## Evaluation-only coordinator conflict resolution

- Fixture: `CF_RICE_01_SCOPE_DISTRICT_OVER_STATE`
- Base scenario: `ANCHOR_PF_PB_BATHINDA_RICE_KHARIF_20251130`
- Rule path: `comparable_domain_and_target → admissibility_gate → geographic_temporal_source_precedence → retain_highest_ranked_claim`
- Resolution: `resolved_by_provenance_precedence`; retained citation(s): `ICAR_CRIDA_CCP`.
- Interpretation: the controlled same-domain source-precedence case verifies deterministic resolution. It is not a real farm observation and is excluded from farmer-facing output.
