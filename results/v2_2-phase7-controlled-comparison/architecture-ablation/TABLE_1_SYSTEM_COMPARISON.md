# Table 1. Architecture comparison over the frozen 300-scenario benchmark

All A1–A6 rows are evaluation-only systems. A0 is the sole farmer-facing architecture. A lower full-pass rate identifies structural requirements intentionally lost by a baseline or ablation; it is not farm-outcome accuracy.

| System | Role | Full structural pass | Direct actions | Run status |
| --- | --- | --- | --- | --- |
| A0 Full MAS | Proposed farmer-facing reference | 300/300 (100.0%) | 0 | completed |
| A1 Regional plan only | Coordinated-MAS baseline | 0/300 (0.0%) | 0 | completed_evaluation_only_with_oracle_failures |
| A2 Centralized RAG | Multi-agent decomposition baseline | 0/300 (0.0%) | 0 | completed_evaluation_only_with_oracle_failures |
| A3 No scoped RAG | Scoped retrieval / operation recovery ablation | 71/300 (23.7%) | 0 | completed_evaluation_only_with_oracle_failures |
| A4 No regional plans | Third-enrichment ablation | 0/300 (0.0%) | 0 | completed_evaluation_only_with_oracle_failures |
| A5 No alignment gates | Integrity-gate ablation; evaluation only | 300/300 (100.0%) | 0 | completed |
| A6 No conflict coordinator | Conflict-resolution ablation | 257/300 (85.7%) | 0 | completed_evaluation_only_with_oracle_failures |
