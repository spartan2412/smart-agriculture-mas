# Data Sources: Provenance and Alignment Fixture Registry

These evaluation-only fixtures do not introduce an external agricultural data source. They derive immutable base identities and plan-row references from the frozen project artifacts below, then apply a labelled in-memory mutation during a test run.

| Frozen artifact | Project path | Use in fixture registry |
| --- | --- | --- |
| Canonical scenario manifest | [`data/scenarios/manifests/scenario_manifest.csv`](../scenarios/manifests/scenario_manifest.csv) | Selects real base scenario/site/crop/state/district/season/date identity and the weather raw-payload hash/path. |
| Regional operation plan | [`data/scenarios/enriched/regional_operation_plan_items.csv`](../scenarios/enriched/regional_operation_plan_items.csv) | Selects one immutable scenario-linked plan item for controlled crop/geography/season/date/scenario-binding overlays. |
| Frozen loader implementation | [`data/benchmark_loader.py`](../benchmark_loader.py) | Supplies the production raw-payload SHA-256 verifier tested by hash fixtures. |
| Alignment validator implementation | [`agents/benchmark/crop_district_season_alignment_validator.py`](../../agents/benchmark/crop_district_season_alignment_validator.py) | Supplies the production cross-layer identity validator tested by plan-item mismatch fixtures. |

The original public data URLs, official document citations, raw paths, and hashes remain documented in [`Documentation/DATA_SOURCES.md`](../../Documentation/DATA_SOURCES.md). This registry never changes them.
