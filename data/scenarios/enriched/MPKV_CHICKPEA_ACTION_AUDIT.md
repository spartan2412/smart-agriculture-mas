# MPKV Maharashtra Chickpea Action-Recovery Audit

| Check | Expected | Actual | Result |
| --- | ---: | ---: | --- |
| official_pdf_and_hash_linked_visual_provenance | 1 | 1 | pass |
| source_quoted_operation_and_field_condition_gates | 1 | 1 | pass |
| full_scope_matrix_and_50_stage_gated_bindings | 300 | 300 | pass |
| combined_catalog_projection | 301 | 301 | pass |
| no_direct_farm_action | 0 | 0 | pass |

## Source-verification boundary

- MPKV's official PDF is retained unchanged with a SHA-256 digest. Its original server response records `Last-Modified: 2023-06-07T11:01:25Z`, and the official publication page names it as Krishi Darshani 2023. The PDF's legacy Marathi font does not yield dependable Unicode extraction.
- The admission record therefore retains 160-dpi rasters of the exact statewide-scope and operation pages, each separately hash-checked, and a limited visual transcription of only the cited passages.
- The guide is dated 7 June 2023 and is treated as persistent state-level technical guidance after that date, not as a dated weekly advisory.
- It binds only Maharashtra chickpea Rabi scenarios and remains conditional on observed hard pods, maturity, and a dry crop; it never becomes a direct farm action.
- No frozen scenario was changed.
