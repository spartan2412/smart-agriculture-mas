"""Create the frozen 30-site Apple-GPU pilot population.

The set contains every existing verified anchor context once, preserving one
scenario per final study site.  It is a reproducibility artifact, not a new
scenario generator or a source of agricultural evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.apple_gpu_preflight import DEFAULT_PILOT_SET_DIR, build_pilot_set


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze the 30 verified anchor scenarios for Apple-GPU pilots.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_PILOT_SET_DIR)
    arguments = parser.parse_args()
    pilot = build_pilot_set(output_dir=arguments.output_dir)
    print(
        json.dumps(
            {
                "output_dir": str(pilot.directory),
                "scenario_count": len(pilot.rows),
                "unique_site_count": pilot.manifest["unique_site_count"],
                "pilot_identity_sha256": pilot.manifest["pilot_identity_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
