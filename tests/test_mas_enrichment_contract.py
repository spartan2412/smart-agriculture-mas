from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.build_mas_enrichment_contract import index_rows


def test_index_rows_rejects_duplicate_scenarios():
    assert index_rows([{"scenario_id": "a"}], "test")["a"]["scenario_id"] == "a"
    try:
        index_rows([{"scenario_id": "a"}, {"scenario_id": "a"}], "test")
    except ValueError as error:
        assert "duplicate" in str(error)
    else:
        raise AssertionError("duplicate scenario IDs must be rejected")
