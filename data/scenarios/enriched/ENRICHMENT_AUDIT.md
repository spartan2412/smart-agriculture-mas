# Enrichment Audit

Generated: 2026-09-26T20:59:55+00:00

This audit checks row identity and source hashes in the additive enrichment layer. An `unavailable` count is not a failure when the source absence is preserved and no value is imputed.

| Layer | Passing | Unavailable | Audit result |
| --- | ---: | ---: | --- |
| regional_management_policy | 300 | 0 | pass |
| regional_calendar | 300 | 0 | pass |
| nasa_power_water_context | 300 | 0 | pass |
| sentinel_scene_context | 296 | 4 | pass |
| sentinel_same_window_recovery | 6 | 8 | pass |
| agmarknet_embedded_market_context | 293 | 7 | pass |
| agmarknet_strict_recovery_feasibility | 0 | 7 | pass |
| mas_enrichment_contract | 300 | 0 | pass |

## Interpretation

- NASA POWER: all passing records have exact-window raw-response hashes.

- Sentinel: a metadata-verified scene is distinct from a usable NDVI pixel. Recovery may use only a clear candidate already present in the original frozen same-month search response; it never overwrites the original selected item.

- Agmarknet: historical comparisons come only from columns in the exact frozen official report. The strict recovery check queries only the three earlier same-crop/district months; a missing comparator produces an abstention, not an estimated price.

- MAS contract: direct irrigation, fertilizer, pesticide treatment, and leaf-vision actions remain abstentions for every scenario.
