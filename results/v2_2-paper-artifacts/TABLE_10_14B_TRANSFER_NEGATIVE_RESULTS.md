# Table 10. 14B Apple-GPU transfer results: verified acceleration, blocked deployment

E2 and E3 both used the immutable v5.1 held-out relevance set and the same pre-registered maximum invalid structured-output rate of 2%. Their Apple-GPU preflights succeeded, but each deployment failed that schema-reliability gate before any 30-site pilot or 300-scenario full-MAS run. The table is therefore a deployment-admission result, not a full-MAS safety, farmer-output, or agricultural-outcome comparison.

| Config. | Backend | Model | Artifact | Apple GPU | Valid | Fact P/R | Safe empty | RAG P/R | Invalid | Fallback | Pilot / full MAS |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E2 | ollama | qwen2.5:14b | gguf | Verified; 9.09 GB resident | 87/96 | 97.3%/100.0% | 96.7% | 100.0%/100.0% | 9.4% | 0.0% | Not run: transfer gate blocked scale-up |
| E3 | mlx-lm | /Users/aryandhumal/Project/data/external/models… | 4-bit | Verified; 8.44 GB resident | 72/96 | 98.6%/100.0% | 96.7% | 100.0%/100.0% | 25.0% | 0.0% | Not run: transfer gate blocked scale-up |

Both deployments selected admitted evidence accurately among parsed responses, but the invalid-output rates—9.4% for E2 and 25.0% for E3—exceeded the 2% gate. E2 and E3 share the Qwen2.5 14B model family but not byte-identical artifacts or quantization formats; their `deployment_backend` label must not be interpreted as an isolated Ollama-versus-MLX runtime comparison.
