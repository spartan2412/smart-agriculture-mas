# Expanded Official RAG Corpus Audit

| Check | Expected | Actual | Result |
| --- | ---: | ---: | --- |
| expanded_source_candidate_coverage | 120 | 120 | pass |
| expanded_source_hashes_and_roles | 78 | 78 | pass |
| expanded_metadata_filtered_scenario_scope | 23400 | 23400 | pass |

## Interpretation

- 78 of 120 candidates were admitted only after source-byte and scope checks.
- The scenario metadata filter admitted 9 exact-week IISR advisory bindings and 670 ICAR-CRIDA historical district-context bindings.
- Historical ICAR-CRIDA documents are retrieval context, not current advice or farm-specific operations.
- Every rejected document remains in the inventory with its reason; it does not contribute chunks or scenario bindings.
