# Scenario Enrichment Layer

This directory contains **additive** evidence derived after the 300-row frozen
scenario benchmark was frozen. It must never overwrite or
reinterpret the source records in `../manifests/`, `../processed/`, or
`../evidence/`.

## First enrichment: existing verified policy context

`scripts/build_existing_policy_enrichment.py` produces four 300-row files from
the benchmark's existing final-management and crop-season evidence:

- `regional_calendar_features.csv` records only the decision month's position
  inside the declared regional season window. It is explicitly **not** observed
  farm phenology or a known sowing/transplant date.
- `management_policy_features.csv` binds every scenario to the final
  crop--state--season fertilizer and conditional IPM sources, their source
  metadata, frozen hashes, page/section locators, PPQS cross-check, and
  conditions.
- `enrichment_evidence_status.csv` records the permitted contextual use and
  the restrictions that remain mandatory.
- `enrichment_provenance.csv` fingerprints every frozen input artifact used by
  the enrichment run.

These records support regional planning and policy explanation. They do not
justify a field-level fertilizer dose, spray, diagnosed disease, threshold
crossing, or observed crop stage.

Run from the repository root:

```bash
.venv-macos/bin/python scripts/build_existing_policy_enrichment.py
```

The completed water, Sentinel, market, official-operation, regional-plan, and
post-harvest sections below are separate additive layers. Each collector or
builder fails closed when its source, identity, hash, or alignment gates do
not pass.

## NASA POWER water context

`scripts/collect_nasa_power_water_context.py` requests additional daily NASA
POWER AG variables for each exact scenario window. It writes raw responses,
their SHA-256 hashes, and source-derived summaries of radiation, modelled
top/root-zone wetness, land evaporation, and precipitation minus land
evaporation. These remain retrospective representative-cell context, never a
field irrigation dose or forecast.

Pilot one or more exact scenarios into a disposable subdirectory first:

```bash
.venv-macos/bin/python scripts/collect_nasa_power_water_context.py \
  --scenario-id ANCHOR_PF_PB_LUDHIANA_RICE_KHARIF_20251130 \
  --out-dir data/scenarios/enriched/pilot
```

## Sentinel-2 NDVI point context

`scripts/collect_sentinel_ndvi_context.py` retrieves each exact frozen
Sentinel-2 item, verifies its identifier, datetime, cloud cover, and nodata
metadata, then samples B04, B08, and SCL through signed cloud-optimized
GeoTIFF reads. It writes a representative-cell NDVI only for a clear SCL
vegetation/not-vegetated land pixel. It never labels the point as the declared
district crop, a farm field, crop stage, or disease observation.

This requires `rasterio`, included in `requirements.txt`. A bounded concurrent
pilot across one anchor per crop can be run as follows:

```bash
.venv-macos/bin/python scripts/collect_sentinel_ndvi_context.py \
  --out-dir data/scenarios/enriched/pilot --workers 3 \
  --scenario-id ANCHOR_PF_PB_LUDHIANA_RICE_KHARIF_20251130 \
  --scenario-id ANCHOR_PF_PB_LUDHIANA_WHEAT_RABI_20260430 \
  --scenario-id ANCHOR_PF_TN_COIMBATORE_MAIZE_RABI_20260331 \
  --scenario-id ANCHOR_PF_MH_JALNA_CHICKPEA_RABI_20260331 \
  --scenario-id ANCHOR_PF_MP_INDORE_SOYBEAN_KHARIF_20251031 \
  --scenario-id ANCHOR_PF_TN_KRISHNAGIRI_TOMATO_RABI_20251231
```

## Non-release Agmarknet extended-lookback experiment

`scripts/collect_agmarknet_market_context.py` keeps the frozen current-month
report and retrieves three exact-source reports for the calendar months before
the decision month. It validates the report's commodity--district--state title
identity, preserves raw report units, and calculates only a unitless historical
trend. It cannot support a price forecast or a sell/hold instruction.

This is **not a MAS input**: during the complete 300-scenario batch the public
endpoint returned rate-limit (`429`) and temporary-service (`503`) responses.
Those results are retained only as an auditable availability experiment. Use
the embedded official-report context below for all MAS work.

```bash
.venv-macos/bin/python scripts/collect_agmarknet_market_context.py \
  --out-dir data/scenarios/enriched/pilot \
  --scenario-id ANCHOR_PF_PB_LUDHIANA_RICE_KHARIF_20251130
```

## Primary Agmarknet context: embedded official comparisons

`scripts/build_embedded_agmarknet_market_context.py` is the primary market
enrichment path. It does **not** make a new API request. Instead, it verifies
the hash of every exact official monthly report already frozen with the
scenario, then uses only its source-published prior-month and
same-calendar-month-prior-year price columns. That produces a directly
auditable historical comparator where the original report contains one, while
leaving the record unavailable where it does not.

This approach avoids rate-limit artifacts from bulk lookback requests and
does not convert a missing official comparison into an estimate.

```bash
.venv-macos/bin/python scripts/build_embedded_agmarknet_market_context.py
```

## Missing-evidence recovery

`scripts/recover_sentinel_ndvi_context.py` is an additive recovery for base
satellite abstentions only. It never changes the frozen selected item. It can
admit only the first clear, coordinate-containing candidate already present in
the original frozen same-month STAC response, ordered by cloud, nodata, and
timestamp. This recovery produced six further source-hashed NDVI contexts;
eight cases remain abstentions.

`scripts/check_market_recovery_feasibility.py` checks the three strictly prior
same-crop/district Agmarknet months for the seven market abstentions. It found
no reported price in any of the 21 exact reports, so no market value was added.

```bash
.venv-macos/bin/python scripts/recover_sentinel_ndvi_context.py
.venv-macos/bin/python scripts/check_market_recovery_feasibility.py
```

See [RECOVERY_FEASIBILITY.md](RECOVERY_FEASIBILITY.md) for the full outcome.

## MAS capability contract

`scripts/build_mas_enrichment_contract.py` combines the audited source status
files into `mas_enrichment_contract.csv`. MAS integration must use this file
to gate each agent's scope. In particular, it permits historical
weather/water, static soil, representative-cell satellite, historical market,
and regional policy **context**, but keeps irrigation actions, farm-specific
fertilizer prescriptions, treatment orders, observed field stage, diagnosis,
and leaf vision as abstentions where no aligned observation exists.

The contract points each available satellite context to either the base or
recovery feature artifact through `satellite_feature_artifact`.

```bash
.venv-macos/bin/python scripts/build_mas_enrichment_contract.py
```

Run the final coverage and hash audit after all builders:

```bash
.venv-macos/bin/python scripts/audit_scenario_enrichment.py
```

## Second enrichment: time-valid official operations and action RAG

This release adds a separate action-evidence layer; it does not rewrite the
frozen scenario facts or relax the capability contract.

1. `scripts/collect_official_rag_sources.py` downloads only sources already
   listed in the registry's regional-management source snapshot. A document is
   admitted only when its SHA-256 exactly matches the frozen snapshot. If an
   official host is temporarily inaccessible, a prior local copy can be reused
   only after it reproduces the same frozen SHA-256.
2. `scripts/build_official_action_enrichment.py` creates
   `official_action_records.csv` from verbatim source passages. The builder
   stops if a quote is not present at the recorded page/section.
3. `scenario_official_action_bindings.csv` provides the complete 300 × action
   applicability matrix. A source may be crop/place/date-valid yet remain
   `conditionally_applicable_pending_unobserved_farm_condition`; this is
   explicitly **not** a farmer instruction.
4. `official_rag_chunks.csv` is the official source corpus, while
   `scenario_rag_scope.csv` is its mandatory pre-retrieval metadata filter.
   It excludes a document outside the scenario's crop, registry geography, or
   effective source window before semantic ranking. PPQS/CIBRC documents are
   regulatory context only, never treatment recommendations.

The source windows are intentionally conservative. A named weekly advisory,
seasonal package, or annual advisory cannot be retrieved for a later decision
date merely because the PDF remains online. Static technical documents are
available only from their conservative issued date forward.

```bash
.venv-macos/bin/python scripts/collect_official_rag_sources.py
.venv-macos/bin/python scripts/build_official_action_enrichment.py
```

See [OFFICIAL_RAG_CORPUS.md](OFFICIAL_RAG_CORPUS.md) for the generated corpus
summary. The raw official source bytes are in
`raw/official_rag_sources/`; extracted page/section text is in
`rag_sources/extracted_text/`.

## Expanded public official RAG sources

The corpus was then expanded without changing the frozen registry or any
scenario fact. It adds two checked source families:

1. ICAR–IISR weekly soybean advisory PDFs discovered from the official
   2021–2024 archives. A weekly document is admitted only when its raw source
   hash is frozen, its extracted content says soybean and exposes Central-Zone
   or Madhya Pradesh/Rajasthan scope, and a scenario falls inside the exact
   issue week.
2. ICAR–CRIDA crop-profile, sowing-window, and weather-contingency PDFs for
   final registered sites. The registry had already recorded their exact raw
   SHA-256 values. These sources are retained as historical district context
   only, never as present-day or farm-specific advice.

`expanded_official_rag_source_candidates.csv` and
`expanded_official_rag_source_rejections.csv` preserve every discovery result.
`expanded_official_rag_source_inventory.csv`,
`expanded_official_rag_chunks.csv`, and `scenario_expanded_rag_scope.csv`
hold the admitted raw material and its complete scenario scope matrix. The
normalized integration artifacts for MAS are:

- `official_rag_corpus_catalog.csv` — 92 admitted sources with their scope,
  role, raw hash, official URL, and usage restriction;
- `official_rag_corpus_all_chunks.csv` — 4,582 provenance-carrying chunks; and
- `scenario_official_rag_scope_all.csv` — 27,600 mandatory pre-ranking
  metadata decisions.

The expanded corpus adds retrieval context, not a new automatic action. It
does not alter the existing 18 source-quoted operation records or relax a
field-data gate. The audit is in
[EXPANDED_OFFICIAL_RAG_AUDIT.md](EXPANDED_OFFICIAL_RAG_AUDIT.md).

```bash
.venv-macos/bin/python scripts/expand_official_rag_corpus.py
.venv-macos/bin/python scripts/audit_expanded_official_rag_corpus.py
.venv-macos/bin/python scripts/build_combined_official_rag_catalog.py
```

## Exact-week soybean operation extraction

The nine scenario records covered by the two exact-week ICAR-IISR soybean
advisories now have a separate, source-quoted action layer. The PDF pages were
visually reviewed, then every stored quote was checked against the matching
hash-verified extracted page. The layer contains 13 operations or guardrails
and a complete 300 × 13 scope matrix:

- `exact_week_iisr_action_records.csv` — operation, method, dose where the
  quoted line states one, conditions, source page, source raw hash, and exact
  weekly issue window;
- `scenario_exact_week_iisr_action_bindings.csv` — every scenario/action
  decision; and
- `official_action_records_all.csv` and
  `scenario_official_action_bindings_all.csv` — normalized 41-action,
  12,300-binding MAS input views.

Fifty-seven pairs pass their document-level scope gates, but all remain
`conditionally_applicable_pending_unobserved_farm_condition`. The record never
converts historical observed weather into a past forecast, a regional nutrient
baseline into a field-specific dose, or a crop-protection guardrail into an
automatic treatment.

```bash
.venv-macos/bin/python scripts/build_exact_week_iisr_action_enrichment.py
.venv-macos/bin/python scripts/build_combined_official_action_catalog.py
```

## Public district/KVK advisory discovery

`scripts/discover_public_district_kvk_advisories.py` checks whether an official
public record can pass all three required gates: crop, exact district, and
issue period covering the scenario decision date. The current check admitted
0/300 exact district advisories. The official KVK portal was not publicly
reachable from this environment and IMD GKMS remains login-gated; available
IISR and CRIDA sources remain labelled zone or historical-district context.
See [PUBLIC_DISTRICT_KVK_ADVISORY_DISCOVERY.md](PUBLIC_DISTRICT_KVK_ADVISORY_DISCOVERY.md).

## Archived district-advisory access check

`scripts/build_archived_advisory_enrichment.py` keeps a strict distinction
between district, state, and zone advice. It probes the official IMD GKMS
portal anonymously and stores the raw access response and its hash. At the
collection time, that entry point returned a sign-in form rather than an
anonymous historical district-bulletin archive. Consequently:

- `scenario_archived_advisory_status.csv` makes no district-advisory claim;
- official ICAR/IISR dated advisories are retained only at their stated
  state/zone scope in `scenario_archived_advisory_bindings.csv`; and
- lack of a public anonymous archive is preserved as unavailable evidence,
  never backfilled with a fabricated district operation.

```bash
.venv-macos/bin/python scripts/build_archived_advisory_enrichment.py
```

## Pre-decision Sentinel NDVI chronology

`scripts/collect_predecision_sentinel_ndvi_timeseries.py` builds a 90-day
pre-decision Sentinel-2 chronology. It reuses the prior source-hashed exact
endpoint observation where it exists, then queries older Sentinel scenes only.
New candidates must pass scene cloud/nodata gates; the temporal sampling plan
uses only source metadata and is made before SCL, reflectance, or NDVI is read.
Only a clear SCL point produces B04/B08 NDVI.

The output contains the raw STAC search payload hash, every attempted
candidate, clear observations, and numeric time-series features. It may support
future non-action signal-divergence evaluation, but it does **not** establish a
crop-labelled parcel, actual crop stage, disease, field moisture, or an action
trigger.

```bash
.venv-macos/bin/python scripts/collect_predecision_sentinel_ndvi_timeseries.py \
  --workers 4 --lookback-days 90 --max-samples 3
```

`scripts/build_natural_signal_divergence_candidates.py` then compares the
numeric direction of a sufficiently recent representative-cell NDVI chronology
with the separately scoped retrospective NASA POWER water context. The output
is not called a crop-stress conflict: it is a controlled set of natural,
cross-source **numerical-divergence candidates** for a future coordinator
evaluation. Every row remains context-only and explains the differing spatial
and temporal scopes.

```bash
.venv-macos/bin/python scripts/build_natural_signal_divergence_candidates.py
```

## Advanced audit

After the six-layer enrichment is complete, run:

```bash
.venv-macos/bin/python scripts/audit_advanced_enrichment.py
```

It verifies source and extraction hashes, verbatim action quotes, complete
scenario–operation and scenario–document matrices, explicit district-advisory
availability, raw STAC payload hashes, pre-decision timestamps, clear-pixel
status, and NDVI arithmetic. The result is written to
`advanced_enrichment_audit.csv` and `ADVANCED_ENRICHMENT_AUDIT.md`.

## Regional operation-plan enrichment

`scripts/build_regional_operation_plan.py` adds a third, farmer-output-oriented
planning layer without changing any frozen scenario fact or issuing a direct
farm action. Every scenario receives three source-linked plan references: its
declared regional season-window position, its regional nutrient-policy source,
and its regional IPM-policy source. Existing source-quoted operations are
included only when their prior crop, geography, season, and source-time binding
already passed; they remain conditional when field preconditions are absent.

The generated artifacts are:

- `regional_operation_plan_summary.csv` — one planning summary per scenario;
- `regional_operation_plan_items.csv` — calendar, policy, and conditional
  source-quoted plan items;
- `regional_operation_plan_provenance.csv` — source-artifact fingerprints;
- `regional_operation_plan_audit.csv` and
  [REGIONAL_OPERATION_PLAN_AUDIT.md](REGIONAL_OPERATION_PLAN_AUDIT.md) —
  coverage, provenance, condition, hash, and direct-action guards.

The current plan has 300 summaries and 1,507 items: three non-action planning
references for each scenario plus 607 source-quoted operations that remain
conditional across 229 scenarios. A transparent PAU recovery layer adds three
public archive-preservation copies of the official annual Kharif package URL
(2023–2025), plus three Rabi packages (2021–22, 2023–24 and 2024–25). PDF year, raw and
extracted hashes, page-quoted operations and conservative archive-derived
availability dates are checked. This admits 83 Punjab rice/wheat conditional
bindings without changing any frozen scenario. The official MPKV *Krishi
Darshani 2023* also supplies a date-gated Maharashtra chickpea hard-pod harvest
operation, recorded through hash-linked visual transcription because its legacy
Marathi font cannot be reliably text-extracted; it adds 50 conditionals. The
other 71 scenarios deliberately retain only calendar and policy plan
references until more time-valid official operations are recovered.

```bash
.venv-macos/bin/python scripts/build_regional_operation_plan.py
.venv-macos/bin/python scripts/audit_regional_operation_plan.py
.venv-macos/bin/python scripts/audit_archived_pau_kharif_action_enrichment.py
.venv-macos/bin/python scripts/audit_mpkv_chickpea_action_enrichment.py
```

See [REGIONAL_OPERATION_PLAN.md](REGIONAL_OPERATION_PLAN.md) for the data
contract and permitted interpretation.

## Fourth enrichment: post-harvest, storage, and logistics

`scripts/build_postharvest_logistics_enrichment.py` adds a source-audited
post-harvest layer without changing the frozen scenario facts or turning a
public directory record into proof of a service. It has two deliberately
separate evidence classes:

1. crop-scoped source-quoted handling practices for maturity, harvest, drying,
   grading, packing, or storage; and
2. collection-date facility, warehouse, state-infrastructure, and static-route
   context.

The layer contains 16 source snapshots, six crop handling profiles, 14
source-quoted handling operations, 700 conditional plan items for all 300
scenarios, 14 exact-crop RAG passages, 90 site-to-facility context links, and
15 static-route records. Handling operations remain conditional because the
benchmark has no observed harvested-lot state. Infrastructure records are
context only: they cannot establish facility/commodity compatibility, capacity,
vacancy, booking, dispatch, vehicle availability, freight, storage duration,
or historical availability.

The active benchmark loader validates every fourth-enrichment raw hash,
scenario/profile/item relationship, candidate reference, route record, and
exact-crop RAG scope before exposing the scenario-specific slice. The
deterministic `PostharvestStorageLogisticsAgent` then emits only conditional
handling and collection-date infrastructure claims. The generic RAG role can
retrieve an exact-crop handling passage only after this scope check; directory
and route context are not retrieved as an operational instruction.

```bash
.venv-macos/bin/python scripts/build_postharvest_logistics_enrichment.py
.venv-macos/bin/python scripts/audit_postharvest_logistics_enrichment.py
.venv-macos/bin/python -m pytest -q tests/test_postharvest_logistics_enrichment.py
```

Read [POSTHARVEST_LOGISTICS_ENRICHMENT.md](POSTHARVEST_LOGISTICS_ENRICHMENT.md)
for the complete artifact contract and
[POSTHARVEST_LOGISTICS_AUDIT.md](POSTHARVEST_LOGISTICS_AUDIT.md) for the eight
passed audit checks. The exact public sources are listed in
[DATA_SOURCES.md](DATA_SOURCES.md) and the final project-wide source register
is [Documentation/DATA_SOURCES.md](../../../Documentation/DATA_SOURCES.md).

## Separate conflict-policy evaluation boundary

The 60 stored records in
[`data/conflict_fixture_registry`](../../conflict_fixture_registry/) are not a
fifth enrichment and are not joined by `FrozenBenchmarkLoader` during a normal
scenario run. They reuse only immutable base identities and existing source
references to test deterministic conflict precedence, safe deferral,
integrity blocking, and false-conflict prevention through labelled in-memory
overlays. They introduce no new agricultural observation, RAG document, or
farmer-facing plan item. See the project
[evaluation policy](../../../Documentation/EVALUATION_POLICY.md) and the
[fixture registry README](../../conflict_fixture_registry/README.md). The
external [oracle evaluation guide](../../../Documentation/ORACLE_EVALUATION_GUIDE.md)
documents how frozen enrichment artifacts are checked after a run without
becoming new farmer-facing evidence.

## Persisted architecture-comparison boundary

The completed A0–A6 comparison reads the frozen enrichment slices only through
the already persisted run manifests and does not rebuild, modify, or broaden
any enrichment. It verifies that every compared run used the same frozen
artifact hashes before deriving structural tables and figures. The report is
available at
[`results/architecture-comparison`](../../../results/architecture-comparison/);
it is evaluation output, not a fifth enrichment or a new source layer.
