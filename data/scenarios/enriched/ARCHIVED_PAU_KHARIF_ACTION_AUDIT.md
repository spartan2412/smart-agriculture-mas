# Archived PAU Kharif Action-Recovery Audit

| Check | Expected | Actual | Result |
| --- | ---: | ---: | --- |
| archive_provenance_and_hashes | 3 | 3 | pass |
| verbatim_operations_and_action_hashes | 6 | 6 | pass |
| full_temporal_scope_matrix_and_stage_gate | 1800 | 1800 | pass |
| combined_catalog_projection | 1806 | 1806 | pass |
| no_direct_farm_action | 0 | 0 | pass |

## Scope

- The replay URLs preserve PAU's original annual package URL; the archive is cited alongside, never instead of, the official publisher.
- Each document self-identifies its Kharif year and each operation is checked verbatim against extracted PDF page 11.
- A recovered operation passes only crop, Punjab geography, Kharif season, and conservative capture-derived date gates. It remains conditional on observed crop maturity.
- No frozen scenario was changed.
