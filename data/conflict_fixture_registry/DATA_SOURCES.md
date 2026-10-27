# Conflict Fixture Registry — Data Sources

This registry introduces **no new external agricultural data source**. Every
fixture is an explicitly labelled evaluation-only overlay. Its base identity
and any real source reference are copied from the frozen, audited artifacts
below.

| Use | Canonical artifact | What is reused | External-source status |
| --- | --- | --- | --- |
| Base scenario identity | [`data/scenarios/manifests/scenario_manifest.csv`](../scenarios/manifests/scenario_manifest.csv) | `scenario_id`, crop, state, district, season, and decision date | Existing frozen public-source scenario evidence; no re-fetch. |
| Real source reference | [`data/scenarios/enriched/regional_operation_plan_items.csv`](../scenarios/enriched/regional_operation_plan_items.csv) | Source document ID, official URL, raw SHA-256 where one is available, and locator | Existing official-source provenance; no new document is admitted. |
| Full provider URLs, citations, restrictions | [`Documentation/DATA_SOURCES.md`](../../Documentation/DATA_SOURCES.md) | Provider-level reference register for registry, scenarios, enrichments, RAG, and post-harvest data | Authoritative project source register. |

The fixture oracle adds no source either: it evaluates the stored runner
outcomes and required fixture-family counts. Its policy and procedure are in
[`Documentation/EVALUATION_POLICY.md`](../../Documentation/EVALUATION_POLICY.md)
and
[`Documentation/ORACLE_EVALUATION_GUIDE.md`](../../Documentation/ORACLE_EVALUATION_GUIDE.md).

## Controlled overlay provenance

The opposing claim in a fixture may use the identifier
`EVALUATION_COUNTERFACTUAL_PROVENANCE_OVERLAY`. This is **not an external
document or a claimed agricultural source**. It marks a deliberate test change
to scope, date validity, provenance completeness, safety status, or identity
metadata.

Each JSON fixture retains `base_source_document_id` and
`base_source_raw_sha256` in metadata, so an evaluator can trace the real
source record on which the test case is anchored. No fixture invents weather,
soil, disease, fertilizer, market, crop-stage, yield, or field observations.
