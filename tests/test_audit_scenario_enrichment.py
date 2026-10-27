from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.audit_scenario_enrichment import audit_table, canonical_payload_hash, response_bytes_hash


def test_audit_table_requires_exact_one_to_one_scenario_coverage():
    expected = {"a", "b"}
    rows = [{"scenario_id": "a"}, {"scenario_id": "b"}]
    audit = audit_table("example", rows, expected, lambda _: True, lambda _: False)
    assert audit["result"] == "pass"
    duplicate = audit_table("example", rows + [{"scenario_id": "a"}], expected, lambda _: True, lambda _: False)
    assert duplicate["result"] == "fail"


def test_canonical_hash_is_order_independent():
    assert canonical_payload_hash({"a": 1, "b": [2]}) == canonical_payload_hash({"b": [2], "a": 1})


def test_response_bytes_hash_preserves_the_raw_evidence(tmp_path):
    payload = tmp_path / "response.json"
    payload.write_bytes(b'{"a": 1}\n')
    assert response_bytes_hash(payload) != canonical_payload_hash({"a": 1})
