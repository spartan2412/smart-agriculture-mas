# Results Index

## Official paper evidence: v2.2

The only result archives that support the current paper are the versioned
`v2_2-*` directories at this level. The release entry point is
[`v2_2-paper-artifacts/`](v2_2-paper-artifacts/), and its
[`OFFICIAL_V2_2_RELEASE_MANIFEST.json`](v2_2-paper-artifacts/OFFICIAL_V2_2_RELEASE_MANIFEST.json)
lists and hashes the 19 canonical v2.2 evidence archives.

The current official result boundary includes:

- deterministic E0/A0, model-enabled E1-v5, and A1–A6 archives;
- the 30-site E1-v5 pilot and its verified Apple-Metal preflight;
- both 60-case fixture archives;
- the Phase 7 comparison, final reproducibility verification, and Phase 10
  paper-artifact package; and
- E2/E3 14B relevance-transfer records, reported transparently as
  structured-output reliability failures rather than admitted full-MAS runs.

## Active support inputs retained at the results root

- [`e1-v5-heldout-final/`](e1-v5-heldout-final/) — frozen one-time v5.1
  held-out bounded-LLM relevance evaluation.
- [`e1-v5-heldout-preflight/`](e1-v5-heldout-preflight/) — its frozen hash and
  runtime preflight manifest.
- [`e2-e3-artifact-binding.json`](e2-e3-artifact-binding.json) — artifact
  binding record used to interpret E2/E3 as a deployment comparison, not a
  pure runtime comparison.

These are retained outside the release archive because active evaluation and
reproduction code reads them. They are inputs/supporting records, not extra
paper-result generations.

## Historical results

Earlier result generations have been preserved, not deleted, in the dated
recoverable hierarchy
[`archive/2026-10-12-pre-v2_2/`](archive/2026-10-12-pre-v2_2/). They must not
be mixed with v2.2 numbers, figures, or paper claims. See that archive's
[`README.md`](archive/2026-10-12-pre-v2_2/README.md) for the exact contents
and original-result purpose.
