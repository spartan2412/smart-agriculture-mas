# Phase 10 Paper Artifacts

This directory is regenerated from frozen data, persisted result archives, and the documented agent contract. It is a presentation layer: it contains no new agricultural evidence, model call, scenario, source retrieval, or manual result entry.

## Reproduce

```bash
.venv-macos/bin/python -m evaluation.paper_artifacts \
  --output-dir results/v2_2-paper-artifacts
```

The command rejects an existing non-empty output directory unless `--overwrite` is passed. `paper_artifact_manifest.json` records every input SHA-256, generator SHA-256, Git state, derived counts, and generated output fingerprint.

## Interpretation boundary

- Structural percentages are exact conformance rates on the frozen 300-scenario population, not agricultural outcome accuracy.
- The bounded-LLM table measures selection among already-admitted source evidence, not farm action correctness.
- Controlled conflict/provenance fixtures are evaluation-only policy tests, never farmer scenarios.
- Runtime panels separate full-MAS, relevance-only, and unaccepted E2/E3 workloads.
- Table 10 reports E2/E3 as verified-acceleration but non-admitted deployment transfers; neither has a pilot or full-MAS result.
