# Advanced Enrichment Audit
Generated: 2026-09-26T20:59:55+00:00
| Layer | Passing | Unavailable | Result |
| --- | ---: | ---: | --- |
| official_source_selection_scope | 14 | 3 | pass |
| official_source_retrieval_and_hashes | 14 | 0 | pass |
| structured_official_action_records | 18 | 0 | pass |
| scenario_operation_bindings | 5400 | 0 | pass |
| metadata_filtered_rag_scope | 231 | 3969 | pass |
| archived_district_advisory_access_and_scope | 0 | 300 | pass |
| predecision_sentinel_ndvi_timeseries | 255 | 45 | pass |
| natural_cross_source_signal_divergence | 43 | 257 | pass |

## Interpretation
- Official documents must reproduce their frozen registry SHA-256 before entering the corpus.
- Every action quote is checked against its recorded source page.
- Metadata filtering happens before retrieval ranking: document crop, registry geography, and effective date must all pass.
- A login-gated public portal is evidence of unavailable anonymous district archive access, not a justification to create a district advisory.
- Sentinel time series contain only pre-decision, clear representative-cell observations. They are not crop, disease, stage, or action labels.
