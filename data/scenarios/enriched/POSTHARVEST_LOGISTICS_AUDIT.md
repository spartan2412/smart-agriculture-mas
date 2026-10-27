# Post-Harvest Storage and Logistics Enrichment Audit

This audit validates only the fourth enrichment. It does not reclassify infrastructure directories as historical operational evidence.

| Check | Expected | Actual | Result |
| --- | ---: | ---: | --- |
| source_snapshot_integrity | 16 | 16 | pass |
| six_crop_profiles_and_direct_action_guard | 6 | 6 | pass |
| source_quoted_operations | 14 | 14 | pass |
| collection_date_infrastructure_integrity | 6931 | 6931 | pass |
| site_context_identity_and_safety | 30 | 30 | pass |
| static_route_context_integrity | 15 | 15 | pass |
| all_300_scenario_bindings | 700 | 700 | pass |
| crop_filtered_postharvest_rag_scope | 700 | 700 | pass |

## Safety interpretation

- Every post-harvest operation remains conditional on an unobserved lot condition; none is a direct farm action.
- NHB and WDRA records are collection-date infrastructure/registration context. They cannot establish capacity, vacancy, commodity acceptance, booking, transport, or historical availability.
- Static OSRM routes are collection-date road-geometry estimates only. They cannot establish traffic, vehicle availability, freight, cold-chain fit, booking, dispatch, or historical access.
- Post-harvest RAG passages are scoped to the exact crop and cannot be retrieved for another crop.
