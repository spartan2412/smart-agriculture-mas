# Table 6. E0 deterministic A0 versus E1-v5 bounded-LLM A0

Both configurations use the same 300 frozen scenarios and data hashes. E1's model is a non-authoritative selector only; both runs use the same external structural oracle. Runtime is descriptive hardware-specific evidence, not a cross-machine speed benchmark.

| Measure | E0 deterministic A0 | E1-v5 bounded-LLM A0 |
| --- | --- | --- |
| Scenario population | 300 (identical) | 300 (identical) |
| Full external-oracle pass | 300/300 (100.0%) | 300/300 (100.0%) |
| Direct farm actions | 0 | 0 |
| Bounded LLM calls | 0 | 2400 |
| LLM acceleration | Not applicable — no LLM backend | Ollama Metal / Apple GPU verified; 4,638,040,390 model bytes resident |
| Mean persisted trace latency | 10.8 ms | 19621.0 ms |
| Maximum persisted trace latency | 106 ms | 25958 ms |
| Maximum Python-process peak RSS | 651476992 | 488079360 |
| Run wall-clock duration | 4.0 s | 5889.0 s |
