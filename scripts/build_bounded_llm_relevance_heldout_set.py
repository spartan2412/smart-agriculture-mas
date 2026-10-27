"""Build the final, non-overwritable v5 held-out relevance set."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.bounded_llm_relevance_heldout import DEFAULT_HELDOUT_SET_DIR, build_heldout_set


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the source-derived final v5 held-out relevance set.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_HELDOUT_SET_DIR)
    arguments = parser.parse_args()
    heldout = build_heldout_set(output_dir=arguments.output_dir)
    print(
        f"Created {len(heldout.questions)} final held-out relevance questions in {heldout.heldout_dir}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
