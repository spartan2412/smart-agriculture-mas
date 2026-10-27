from pathlib import Path
import sys
import csv
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.build_source_scoped_final_admission import close_coordinate, rows_at_cell


def test_coordinate_gate_accepts_collector_rounding_but_not_a_different_cell():
    cell = {"longitude": "75.123456", "latitude": "30.123456"}
    assert close_coordinate("75.12346", cell["longitude"]) is True
    assert rows_at_cell([{"longitude": "75.12346", "latitude": "30.12346"}], cell) is True
    assert rows_at_cell([{"longitude": "75.12400", "latitude": "30.12346"}], cell) is False


def test_frozen_source_scoped_manifest_contains_only_fully_admitted_five_per_crop_sites():
    registry = Path(__file__).resolve().parent.parent / "data" / "registry"
    with (registry / "source_scoped_final_site_admission.csv").open(newline="", encoding="utf-8") as source_file:
        admissions = list(csv.DictReader(source_file))
    with (registry / "final_study_sites.csv").open(newline="", encoding="utf-8") as source_file:
        manifest = list(csv.DictReader(source_file))

    assert len(admissions) == 30
    assert len(manifest) == 30
    assert all(row["admission_status"] == "admitted" for row in admissions)
    assert all(row["freeze_status"] == "admitted" for row in manifest)
    assert Counter(row["crop"] for row in manifest) == {
        "rice": 5, "wheat": 5, "maize": 5, "chickpea": 5, "soybean": 5, "tomato": 5,
    }
    assert {row["site_id"] for row in admissions} == {row["site_id"] for row in manifest}
