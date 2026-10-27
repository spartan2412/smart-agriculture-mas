# Table 7. E1-v5 bounded-LLM runtime behavior over 300 scenarios

This is execution behavior, not model-quality accuracy. Selection quality is reported separately from the immutable held-out set in Table 8.

| Role | Calls | Accepted | Fallback | Invalid/rejected | Accepted empty | Selected IDs |
| --- | --- | --- | --- | --- | --- | --- |
| farmer_explanation_citation_agent | 300 | 300 | 0 | 0 | 0 | 300 |
| fertilizer_baseline_agent | 300 | 300 | 0 | 0 | 0 | 600 |
| market_evidence_agent | 300 | 300 | 0 | 0 | 7 | 293 |
| official_operations_rag_agent | 300 | 300 | 0 | 0 | 0 | 300 |
| provenance_aware_coordinator_agent | 300 | 300 | 0 | 0 | 0 | 300 |
| satellite_ndvi_context_agent | 300 | 300 | 0 | 0 | 13 | 287 |
| soil_context_agent | 300 | 300 | 0 | 0 | 0 | 300 |
| weather_context_agent | 300 | 300 | 0 | 0 | 0 | 300 |
