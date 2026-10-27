# Table 3. Main structural-conformance results over the frozen 300 scenarios

A0/E0 is the deterministic full-MAS reference. A1–A6 are declared evaluation-only baselines or ablations. A rate is an exact independent-oracle conformance rate over the fixed benchmark, **not** irrigation, yield, disease, fertilizer-dose, market-profit, or general agricultural accuracy.

| System | Role | All structural checks | Grounded plan coverage | Conditional-operation completeness | Plan citation coverage | RAG scope compliance | Conflict trace compliance | Safety / permissions | Direct farm actions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A0 Full MAS | Proposed farmer-facing reference | 300/300 (100.0%) | 300/300 (100.0%) | 300/300 (100.0%) | 300/300 (100.0%) | 300/300 (100.0%) | 300/300 (100.0%) | 300/300 (100.0%) | 0 |
| A1 Regional plan only | Coordinated-MAS baseline | 0/300 (0.0%) | 300/300 (100.0%) | 0/300 (0.0%) | 101/300 (33.7%) | 300/300 (100.0%) | 300/300 (100.0%) | 300/300 (100.0%) | 0 |
| A2 Centralized RAG | Multi-agent decomposition baseline | 0/300 (0.0%) | 0/300 (0.0%) | 0/300 (0.0%) | 0/300 (0.0%) | 300/300 (100.0%) | 300/300 (100.0%) | 300/300 (100.0%) | 0 |
| A3 No scoped RAG | Scoped retrieval / operation recovery ablation | 71/300 (23.7%) | 300/300 (100.0%) | 71/300 (23.7%) | 197/300 (65.7%) | 300/300 (100.0%) | 300/300 (100.0%) | 300/300 (100.0%) | 0 |
| A4 No regional plans | Third-enrichment ablation | 0/300 (0.0%) | 0/300 (0.0%) | 71/300 (23.7%) | 0/300 (0.0%) | 300/300 (100.0%) | 300/300 (100.0%) | 300/300 (100.0%) | 0 |
| A5 No alignment gates | Integrity-gate ablation; evaluation only | 300/300 (100.0%) | 300/300 (100.0%) | 300/300 (100.0%) | 300/300 (100.0%) | 300/300 (100.0%) | 300/300 (100.0%) | 300/300 (100.0%) | 0 |
| A6 No conflict coordinator | Conflict-resolution ablation | 257/300 (85.7%) | 300/300 (100.0%) | 300/300 (100.0%) | 300/300 (100.0%) | 300/300 (100.0%) | 257/300 (85.7%) | 300/300 (100.0%) | 0 |

A5 equals A0 on valid normal inputs because all 300 records were admitted as aligned; its protective value is measured only by the controlled malformed-bundle fixtures in Table 6.
