"""Build the independent source-derived bounded-LLM development question set."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.bounded_llm_relevance_development import (
    DEFAULT_DEVELOPMENT_SET_DIR,
    build_development_set,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the source-derived development-only bounded-LLM relevance set."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DEVELOPMENT_SET_DIR)
    arguments = parser.parse_args()
    development_set = build_development_set(output_dir=arguments.output_dir)
    print(
        f"Created {len(development_set.questions)} development-only relevance questions in "
        f"{development_set.development_dir} for "
        f"{len(development_set.manifest['roles'])} bounded-LLM roles."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
