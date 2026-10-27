"""Create the frozen source-derived relevance benchmark from existing evidence."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.bounded_llm_relevance import DEFAULT_BENCHMARK_DIR, build_relevance_benchmark


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the 96-question source-derived bounded-LLM relevance benchmark."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_BENCHMARK_DIR)
    arguments = parser.parse_args()
    benchmark = build_relevance_benchmark(output_dir=arguments.output_dir)
    print(
        f"Frozen {len(benchmark.questions)} relevance questions in {benchmark.benchmark_dir} "
        f"for {len(benchmark.manifest['roles'])} bounded-LLM roles."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
