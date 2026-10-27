from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.recover_sentinel_ndvi_context import in_declared_window


def test_in_declared_window_accepts_boundaries_and_rejects_outside_dates():
    window = "2025-03-01T00:00:00Z/2025-03-31T23:59:59Z"
    assert in_declared_window("2025-03-01T00:00:00Z", window)
    assert in_declared_window("2025-03-31T23:59:59Z", window)
    assert not in_declared_window("2025-02-28T23:59:59Z", window)
