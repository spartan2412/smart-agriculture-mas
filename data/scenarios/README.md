# Scenario Data

This directory contains scenario records generated from the frozen
30/30-admitted site registry. It does not modify data/registry.

## Current scope

The dataset contains 300 verified public-data contexts:

- 30 fixed anchor contexts: one fully-admitted decision window per final site.
- 270 supplementary contexts: nine independent, all-gate-passing historical
  months per site.

Every supplementary context stores its own exact NASA POWER daily response,
Agmarknet crop--district monthly report, and same-month Sentinel-2 L2A STAC
response. Soil data remain the fixed SoilGrids profile for the registered
representative cell. Management documents remain source links only.

Candidate months are searched newest-first inside each final registry season
window from 2016 onward, excluding the anchor month, and are admitted only
when every source gate passes. The only documented post-anchor exception is
tomato: its exact Krishnagiri market archive supplied only six pre-anchor
all-gate months, so January--March 2026 (the same declared October--March
rabi window) are allowed under a fixed 2026-03-31 source cutoff. The manifest
labels each row as pre- or post-anchor, and no later source data are used.

## Non-synthetic data policy

- Weather is downloaded from the exact fixed NASA POWER URL.
- Market values are downloaded from the exact fixed Agmarknet report URL.
- Soil and Sentinel fields come from the admitted registry artifacts.
- Supplementary Sentinel fields come from a raw STAC response for the same
  calendar month; a scenario is rejected when no item meets cloud <= 30% and
  nodata <= 10%.
- A disease event is never inferred from a crop-protection document.
- Crop stage is never inferred from a district calendar without field
  phenology evidence.
- Regional fertilizer sources are retained as evidence links only. They do not
  become farm-specific fertilizer schedules.
- Protection action remains unavailable unless a dated diagnosis or threshold
  event is independently archived for that scenario.

The manifest uses explicit unavailable statuses for these unsupported claims.
They must not be converted to zero, no disease, or a default action.

## Generated files

- manifests/anchor_scenario_manifest.csv — immutable scenario identity and
  provenance.
- manifests/supplementary_scenario_manifest.csv — 270 date-specific,
  source-gated historical contexts.
- manifests/scenario_manifest.csv — consolidated 300-row manifest.
- processed/anchor_scenario_features.csv — source-derived weather, static
  soil, Sentinel metadata, and market summary fields.
- processed/supplementary_scenario_features.csv and
  processed/scenario_features.csv — supplementary and consolidated feature
  views.
- evidence/anchor_scenario_evidence_status.csv — mandatory abstention and
  management-evidence constraints.
- evidence/supplementary_scenario_evidence_status.csv and
  evidence/scenario_evidence_status.csv — supplementary and consolidated
  evidence views.
- raw/nasa_power/, raw/agmarknet/, and raw/sentinel/ — exact public source
  payloads for the supplementary records (the anchors predate the
  date-specific Sentinel raw-payload collection).
- manifests/anchor_scenario_rejections.csv — any source/date/location
  failures. A rejected row is not a scenario.
- manifests/supplementary_scenario_candidate_rejections.csv — candidate
  failures encountered while completing the final resume pass. It is an
  operational trace, not a scenario file.

Run the generator from the repository root:

    .venv-macos/bin/python scripts/generate_anchor_scenarios.py

    .venv-macos/bin/python scripts/generate_supplementary_scenarios.py

Do not duplicate, perturb, interpolate, or synthesize records to extend this
benchmark. Any future decision date requires a separate evidence-gated
collection pass and an explicit source-time policy.

## Downstream enrichment boundary

The four enrichment layers do not modify any file in this directory. They add
source-linked contextual evidence, official RAG/action records, regional plan
items, and post-harvest/storage/logistics context in
[`enriched/`](enriched/). The active benchmark loader joins those artifacts only
after their identity, scope, provenance, and raw-hash checks pass. See
[`enriched/README.md`](enriched/README.md) and the project-wide
[source register](../../Documentation/DATA_SOURCES.md).

The separate 60-case
[`conflict fixture registry`](../conflict_fixture_registry/README.md) is also
outside this directory's data population. It references immutable base-scenario
identities but never edits, extends, relabels, or loads as one of the 300
scenario rows. Its controlled overlays are evaluation-only policy tests, not
historical agricultural scenarios.

After a normal scenario run is complete, the external oracle compares its
trace only with this frozen scenario bundle and the joined enrichment evidence.
It does not modify scenario data or add a new source. The formal boundary and
reproduction procedure are in
[`Documentation/EVALUATION_POLICY.md`](../../Documentation/EVALUATION_POLICY.md)
and
[`Documentation/ORACLE_EVALUATION_GUIDE.md`](../../Documentation/ORACLE_EVALUATION_GUIDE.md).

## Persisted experiment-output boundary

The completed A0–A6 architecture comparison is downstream of this directory:
it never changes a scenario row, enrichment record, raw payload, or source
hash. It verifies the identical 300-scenario IDs and frozen-input hashes from
the persisted run manifests, then reports exact structural conformance in
[`results/architecture-comparison`](../../results/architecture-comparison/).
Those derived results are evaluation artifacts, not new scenario evidence or
farm-outcome labels.

### Why a 300/300 A0 structural result is expected

The normal scenario set is deliberately valid by construction: each row enters
only after its identity, crop--district--season--date scope, source status,
and frozen payload requirements pass. With every runtime gate enabled and no
LLM in deterministic A0, a 300/300 oracle rate means the final trace retained
the 18 admitted evidence-and-safety invariants. It does **not** measure
agricultural outcomes or establish 100% recommendation accuracy. The oracle
is implemented outside the runtime path, but it checks the same frozen public
source contract rather than independent farm labels. Its protective value is
demonstrated separately by intentionally bad traces, component ablations, and
the malformed provenance fixtures. See
[`Documentation/RESULTS.md`](../../Documentation/RESULTS.md) for the complete
interpretation and permitted paper wording.
