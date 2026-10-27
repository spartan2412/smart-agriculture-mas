# Table 9. Runtime and backend measurements

Full-MAS runtime and held-out relevance runtime are distinct measurements and must not be compared as the same workload. Memory is descriptive process peak RSS/measurement output, not an isolated model-memory benchmark. E2/E3 are retained as transparent structured-output-gate negative results and have no 30-site or 300-scenario full-MAS run.

## Full 300-scenario MAS workloads

| Configuration | System | Scenarios | Structural pass | LLM calls | Mean trace ms | Max trace ms | Peak MiB | Wall s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E0 | Deterministic full MAS | 300 | 300/300 (100.0%) | 0 | 10.8 | 106.0 | 621.3 | 4.0 |
| E1-v5 | Bounded-LLM full MAS | 300 | 300/300 (100.0%) | 2400 | 19621.0 | 25958.0 | 465.5 | 5889.0 |

## Held-out relevance runtime / deployment observations

| Configuration | Backend | Model | Questions | Result state | Mean ms | P95 ms | Invalid | Fallback | Peak MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E1-v5.1 | ollama | qwen2.5:7b-instruct | 96 | accepted | 2470.5 | 4434.0 | 0.0% | 0.0% | 97.5 |
| E2 | ollama | qwen2.5:14b | 96 | not accepted (structured-output gate) | 6431.2 | 12402.0 | 9.4% | 0.0% | 103.7 |
| E3 | mlx-lm | /Users/aryandhumal/Project/data/external/models/mlx-community--Qwen2.5-14B-Instruct-4bit | 96 | not accepted (structured-output gate) | 7876.3 | 12577.0 | 25.0% | 0.0% | 1232.7 |
