"""Build evaluation-only provenance and alignment integrity fixtures.

The 300 frozen benchmark scenarios remain immutable.  This builder creates a
separate registry of controlled, *single-fault* overlays which test whether
the production integrity boundary rejects a mismatched bundle before any
farmer-facing agent can run.  They are not agricultural observations and must
never be admitted to ``data/registry`` or the normal benchmark population.
"""
from __future__ import annotations

import csv
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_ROOT = PROJECT_ROOT / "data" / "provenance_fixture_registry"
FIXTURES_ROOT = REGISTRY_ROOT / "fixtures"
SCENARIO_MANIFEST = PROJECT_ROOT / "data" / "scenarios" / "manifests" / "scenario_manifest.csv"
PLAN_ITEMS = PROJECT_ROOT / "data" / "scenarios" / "enriched" / "regional_operation_plan_items.csv"

FIXTURE_SCHEMA_VERSION = "1.0"
EVALUATION_ONLY_LABEL = "evaluation_only_counterfactual_not_real_farm_evidence"
FOCUSED_CROPS = ("rice", "wheat", "maize", "chickpea", "soybean", "tomato")
BASE_IDENTITY_FIELDS = (
    "scenario_id",
    "site_id",
    "crop",
    "state",
    "district",
    "season",
    "decision_date",
)

# Ten fixtures in each class gives a total of 60.  The first five classes are
# caught by the production alignment validator.  The final class is caught by
# the loader's raw-payload verifier before either A0 or A5 can start.  This
# distinction is intentional: EvidenceProvenanceAgent reports provenance, but
# immutable payload-hash validation is a loader responsibility.
FAULT_SPECS: tuple[Mapping[str, str], ...] = (
    {
        "fixture_type": "plan_item_crop_scope_mismatch",
        "fixture_family": "alignment_validator_rejection",
        "target_layer": "regional_operation_plan_item",
        "field": "crop",
        "expected_a0_status": "blocked_by_alignment_validator",
        "expected_a5_status": "exposed_past_omitted_alignment_validator",
    },
    {
        "fixture_type": "plan_item_district_scope_mismatch",
        "fixture_family": "alignment_validator_rejection",
        "target_layer": "regional_operation_plan_item",
        "field": "district",
        "expected_a0_status": "blocked_by_alignment_validator",
        "expected_a5_status": "exposed_past_omitted_alignment_validator",
    },
    {
        "fixture_type": "plan_item_season_scope_mismatch",
        "fixture_family": "alignment_validator_rejection",
        "target_layer": "regional_operation_plan_item",
        "field": "season",
        "expected_a0_status": "blocked_by_alignment_validator",
        "expected_a5_status": "exposed_past_omitted_alignment_validator",
    },
    {
        "fixture_type": "plan_item_decision_date_scope_mismatch",
        "fixture_family": "alignment_validator_rejection",
        "target_layer": "regional_operation_plan_item",
        "field": "decision_date",
        "expected_a0_status": "blocked_by_alignment_validator",
        "expected_a5_status": "exposed_past_omitted_alignment_validator",
    },
    {
        "fixture_type": "plan_item_scenario_binding_mismatch",
        "fixture_family": "alignment_validator_rejection",
        "target_layer": "regional_operation_plan_item",
        "field": "scenario_id",
        "expected_a0_status": "blocked_by_alignment_validator",
        "expected_a5_status": "exposed_past_omitted_alignment_validator",
    },
    {
        "fixture_type": "weather_payload_hash_mismatch",
        "fixture_family": "loader_payload_integrity_rejection",
        "target_layer": "manifest",
        "field": "weather_current_response_sha256",
        "expected_a0_status": "blocked_by_loader_payload_hash_verifier",
        "expected_a5_status": "blocked_by_loader_payload_hash_verifier",
    },
)

MANIFEST_FIELDS = (
    "fixture_id",
    "fixture_schema_version",
    "fixture_classification",
    "fixture_family",
    "fixture_type",
    "target_layer",
    "base_scenario_id",
    "base_site_id",
    "crop",
    "state",
    "district",
    "season",
    "decision_date",
    "controlled_change_only",
    "expected_a0_status",
    "expected_a5_status",
    "expected_direct_farm_action_issued",
    "fixture_content_sha256",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def canonical_sha256(payload: Mapping[str, Any]) -> str:
    """Hash one fixture independently of its self-reported checksum."""
    stable = dict(payload)
    stable.pop("fixture_content_sha256", None)
    encoded = json.dumps(stable, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _choose_base_scenarios() -> tuple[dict[str, str], ...]:
    """Select one deterministic real scenario for each of the 30 final sites."""
    by_site: dict[str, list[dict[str, str]]] = {}
    for row in read_csv(SCENARIO_MANIFEST):
        if row["crop"] in FOCUSED_CROPS:
            by_site.setdefault(row["site_id"], []).append(row)
    if len(by_site) != 30:
        raise ValueError(f"Expected 30 final crop--location sites, found {len(by_site)}")
    bases = tuple(
        sorted(rows, key=lambda row: row["scenario_id"])[0]
        for _site_id, rows in sorted(by_site.items())
    )
    crop_counts = Counter(row["crop"] for row in bases)
    if crop_counts != Counter({crop: 5 for crop in FOCUSED_CROPS}):
        raise ValueError(f"Expected five base sites per focused crop, found {dict(crop_counts)}")
    return bases


def _plan_items_by_scenario() -> dict[str, tuple[dict[str, str], ...]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in read_csv(PLAN_ITEMS):
        grouped.setdefault(row["scenario_id"], []).append(row)
    return {
        scenario_id: tuple(sorted(rows, key=lambda row: row["plan_item_id"]))
        for scenario_id, rows in grouped.items()
    }


def _alternative_value(field: str, base: Mapping[str, str], all_scenarios: Sequence[Mapping[str, str]]) -> str:
    """Return a real-but-inapplicable identity value, never an observation."""
    current = base[field]
    if field == "crop":
        return next(crop for crop in FOCUSED_CROPS if crop != current)
    if field == "season":
        return "rabi" if current != "rabi" else "kharif"
    for candidate in all_scenarios:
        value = candidate[field]
        if value != current:
            return value
    raise ValueError(f"No alternative frozen {field} exists for {base['scenario_id']}")


def _plan_item_for(base: Mapping[str, str], plan_items: Mapping[str, Sequence[Mapping[str, str]]]) -> Mapping[str, str]:
    rows = plan_items.get(base["scenario_id"], ())
    if not rows:
        raise ValueError(f"Base scenario lacks regional plan rows: {base['scenario_id']}")
    # The first stable row is enough: every populated identity field is checked
    # by the real alignment agent, and no operation text/source is altered.
    return rows[0]


def _source_reference(item: Mapping[str, str]) -> dict[str, str]:
    return {
        "source_document_id": item.get("source_document_id", ""),
        "source_url": item.get("source_url", ""),
        "source_raw_sha256": item.get("source_raw_sha256", ""),
        "source_location": item.get("source_location", ""),
    }


def _build_fixture(
    *,
    fixture_id: str,
    spec: Mapping[str, str],
    base: Mapping[str, str],
    plan_items: Mapping[str, Sequence[Mapping[str, str]]],
    all_scenarios: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    target_layer = spec["target_layer"]
    field = spec["field"]
    if target_layer == "regional_operation_plan_item":
        item = _plan_item_for(base, plan_items)
        base_value = item.get(field, "")
        if base_value != base[field]:
            raise ValueError(
                f"Plan item base identity is not aligned for {base['scenario_id']}: {field}"
            )
        counterfactual_value = _alternative_value(field, base, all_scenarios)
        selector = {"plan_item_id": item["plan_item_id"]}
        source_reference = _source_reference(item)
    elif target_layer == "manifest":
        base_value = base.get(field, "")
        if not base_value or len(base_value) != 64:
            raise ValueError(f"Base scenario has no SHA-256 payload value for {base['scenario_id']}")
        counterfactual_value = "0" * 64
        selector = {"scenario_id": base["scenario_id"]}
        source_reference = {
            "source_document_id": "FROZEN_SCENARIO_MANIFEST",
            "source_url": "",
            "source_raw_sha256": base_value,
            "source_location": base.get("weather_raw_path", ""),
        }
    else:  # pragma: no cover - fixture spec is an internal constant
        raise ValueError(f"Unsupported fixture target layer: {target_layer}")
    if base_value == counterfactual_value:
        raise ValueError(f"Fixture would not change {field}: {fixture_id}")

    fixture = {
        "fixture_id": fixture_id,
        "fixture_schema_version": FIXTURE_SCHEMA_VERSION,
        "fixture_classification": EVALUATION_ONLY_LABEL,
        "fixture_family": spec["fixture_family"],
        "fixture_type": spec["fixture_type"],
        "base_scenario": {field: base[field] for field in BASE_IDENTITY_FIELDS},
        "base_source_reference": source_reference,
        "controlled_change_only": True,
        "overlay": {
            "target_layer": target_layer,
            "selector": selector,
            "field": field,
            "base_value": base_value,
            "counterfactual_value": counterfactual_value,
            "classification": "controlled_single_fault_not_real_evidence",
        },
        "expected": {
            "a0_status": spec["expected_a0_status"],
            "a5_status": spec["expected_a5_status"],
            "direct_farm_action_issued": False,
        },
    }
    fixture["fixture_content_sha256"] = canonical_sha256(fixture)
    return fixture


def build_fixtures() -> list[dict[str, Any]]:
    """Build 60 fixtures: six fault classes × ten cases each."""
    bases = _choose_base_scenarios()
    all_scenarios = tuple(read_csv(SCENARIO_MANIFEST))
    plan_items = _plan_items_by_scenario()
    fixtures: list[dict[str, Any]] = []
    # Every base site appears once in each pass.  The shifted second pass gives
    # every site two *different* fault classes while preserving 10/type.
    for pass_index, shift in enumerate((0, 3), start=1):
        for base_index, base in enumerate(bases):
            spec = FAULT_SPECS[(base_index + shift) % len(FAULT_SPECS)]
            fixture_id = f"PAF_{pass_index}_{base_index + 1:02d}_{spec['fixture_type'].upper()}"
            fixtures.append(
                _build_fixture(
                    fixture_id=fixture_id,
                    spec=spec,
                    base=base,
                    plan_items=plan_items,
                    all_scenarios=all_scenarios,
                )
            )
    expected_type_counts = Counter({spec["fixture_type"]: 10 for spec in FAULT_SPECS})
    actual_type_counts = Counter(fixture["fixture_type"] for fixture in fixtures)
    if len(fixtures) != 60 or actual_type_counts != expected_type_counts:
        raise AssertionError(f"Unexpected provenance-fixture composition: {dict(actual_type_counts)}")
    return fixtures


def _write_fixture(path: Path, fixture: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(fixture, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_readme() -> None:
    lines = [
        "# Evaluation-Only Provenance and Alignment Fixture Registry",
        "",
        "This registry stores **60 reproducible, single-fault counterfactual fixtures** for testing the frozen benchmark's integrity boundary. It is separate from the 30-site registry, four agricultural enrichments, 300 frozen scenarios, and the 60 conflict-resolution fixtures.",
        "",
        "Every fixture starts from one immutable real scenario, then applies one in-memory identity/binding or payload-hash mutation. It contains no weather, soil, disease, market, fertilizer, crop-stage, yield, or farm observation and is never supplied to the farmer-facing MAS workflow.",
        "",
        "## What this evaluates",
        "",
        "| Fault class | Cases | Production boundary under test | Expected A0 result | Expected A5 result |",
        "| --- | ---: | --- | --- | --- |",
        "| Plan item crop scope mismatch | 10 | Crop--District--Season Alignment Validator | Block | Exposed past omitted validator |",
        "| Plan item district scope mismatch | 10 | Crop--District--Season Alignment Validator | Block | Exposed past omitted validator |",
        "| Plan item season scope mismatch | 10 | Crop--District--Season Alignment Validator | Block | Exposed past omitted validator |",
        "| Plan item decision-date scope mismatch | 10 | Crop--District--Season Alignment Validator | Block | Exposed past omitted validator |",
        "| Plan-item scenario binding mismatch | 10 | Crop--District--Season Alignment Validator | Block | Exposed past omitted validator |",
        "| Weather payload SHA-256 mismatch | 10 | Frozen loader raw-payload verifier | Block | Block |",
        "",
        "A5 omits the alignment validator and the provenance-trace agent by design. It does **not** bypass the loader: payload hash verification remains a shared immutable-input boundary for A0 and A5. The `EvidenceProvenanceAgent` is an auditable provenance summary, not a second hash validator; this registry records that architectural distinction rather than claiming a nonexistent check.",
        "",
        "## Coverage and safety boundary",
        "",
        "- 60 fixtures total: 10 per fault class, 10 per focused crop, and two per each of the 30 final crop--location sites.",
        "- A fixture is a test of rejection/exposure behaviour, not a real farm event or agricultural outcome.",
        "- A5 exposure stops at its evaluation-only gate boundary. The runner never executes downstream agents, coordinator, or farmer message on an invalid bundle.",
        "- All expected direct-farm-action values are `false` and no decision object is constructed for a fixture.",
        "",
        "## Contents",
        "",
        "| Artifact | Purpose |",
        "| --- | --- |",
        "| `provenance_fixture_manifest.csv` | One-row index with expected A0/A5 outcomes and checksum. |",
        "| `fixtures/*.json` | Full labelled in-memory overlay for each controlled fault. |",
        "| `PROVENANCE_FIXTURE_AUDIT.md` | Coverage and expected-result audit. |",
        "| `DATA_SOURCES.md` | Exact frozen project artifacts from which identities and plan rows are derived. |",
        "",
        "## Rebuild and evaluate",
        "",
        "```bash",
        ".venv-macos/bin/python scripts/build_provenance_fixture_registry.py",
        ".venv-macos/bin/python -m evaluation.provenance_fixture_runner --output-dir results/provenance-gate-fixtures",
        "```",
        "",
        "The normal benchmark path never imports these fixtures. See [the evaluation policy](../../Documentation/EVALUATION_POLICY.md) and [oracle guide](../../Documentation/ORACLE_EVALUATION_GUIDE.md) for paper-facing interpretation.",
    ]
    (REGISTRY_ROOT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_data_sources() -> None:
    lines = [
        "# Data Sources: Provenance and Alignment Fixture Registry",
        "",
        "These evaluation-only fixtures do not introduce an external agricultural data source. They derive immutable base identities and plan-row references from the frozen project artifacts below, then apply a labelled in-memory mutation during a test run.",
        "",
        "| Frozen artifact | Project path | Use in fixture registry |",
        "| --- | --- | --- |",
        "| Canonical scenario manifest | [`data/scenarios/manifests/scenario_manifest.csv`](../scenarios/manifests/scenario_manifest.csv) | Selects real base scenario/site/crop/state/district/season/date identity and the weather raw-payload hash/path. |",
        "| Regional operation plan | [`data/scenarios/enriched/regional_operation_plan_items.csv`](../scenarios/enriched/regional_operation_plan_items.csv) | Selects one immutable scenario-linked plan item for controlled crop/geography/season/date/scenario-binding overlays. |",
        "| Frozen loader implementation | [`data/benchmark_loader.py`](../benchmark_loader.py) | Supplies the production raw-payload SHA-256 verifier tested by hash fixtures. |",
        "| Alignment validator implementation | [`agents/benchmark/crop_district_season_alignment_validator.py`](../../agents/benchmark/crop_district_season_alignment_validator.py) | Supplies the production cross-layer identity validator tested by plan-item mismatch fixtures. |",
        "",
        "The original public data URLs, official document citations, raw paths, and hashes remain documented in [`Documentation/DATA_SOURCES.md`](../../Documentation/DATA_SOURCES.md). This registry never changes them.",
    ]
    (REGISTRY_ROOT / "DATA_SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_audit(fixtures: Sequence[Mapping[str, Any]]) -> None:
    type_counts = Counter(fixture["fixture_type"] for fixture in fixtures)
    crop_counts = Counter(fixture["base_scenario"]["crop"] for fixture in fixtures)
    site_counts = Counter(fixture["base_scenario"]["site_id"] for fixture in fixtures)
    lines = [
        "# Provenance and Alignment Fixture Audit",
        "",
        f"- Schema version: `{FIXTURE_SCHEMA_VERSION}`",
        f"- Classification: `{EVALUATION_ONLY_LABEL}`",
        "- Frozen registry, scenarios, enrichments, source artifacts, and normal workflow: unchanged.",
        "- Each stored fixture contains one controlled in-memory mutation only.",
        "- No fixture can create a farm action, be loaded by the normal scenario loader, or enter a farmer-facing run.",
        "",
        "## Coverage",
        "",
        "| Fault class | Cases |",
        "| --- | ---: |",
        *(f"| {fixture_type} | {type_counts[fixture_type]} |" for fixture_type in sorted(type_counts)),
        "",
        "| Crop | Cases |",
        "| --- | ---: |",
        *(f"| {crop} | {crop_counts[crop]} |" for crop in FOCUSED_CROPS),
        "",
        f"All **{len(site_counts)}** final crop--location sites are represented exactly twice.",
        "",
        "## Required outcomes",
        "",
        "- A0 blocks all 50 plan-item identity/binding mismatches at the real alignment validator.",
        "- A5 exposes those same 50 invalid bundles past its intentionally omitted alignment validator, but the evaluation runner halts there; it never calls downstream agents or creates a farmer decision.",
        "- Both A0 and A5 block all 10 payload-hash mismatches at the shared frozen loader verifier.",
        "- No fixture creates a direct farm action or measures agricultural correctness.",
    ]
    (REGISTRY_ROOT / "PROVENANCE_FIXTURE_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_registry(registry_root: Path = REGISTRY_ROOT) -> list[dict[str, Any]]:
    """Fail closed if a fixture loses its provenance, coverage, or safety boundary."""
    manifest = read_csv(registry_root / "provenance_fixture_manifest.csv")
    if len(manifest) != 60 or len({row["fixture_id"] for row in manifest}) != 60:
        raise ValueError("Fixture manifest must contain exactly 60 unique rows")
    scenarios = {row["scenario_id"]: row for row in read_csv(SCENARIO_MANIFEST)}
    plan_items = {
        row["plan_item_id"]: row
        for row in read_csv(PLAN_ITEMS)
    }
    fixtures: list[dict[str, Any]] = []
    type_counts: Counter[str] = Counter()
    crop_counts: Counter[str] = Counter()
    site_counts: Counter[str] = Counter()
    expected_by_type = {spec["fixture_type"]: spec for spec in FAULT_SPECS}
    for row in manifest:
        fixture_path = registry_root / "fixtures" / f"{row['fixture_id']}.json"
        if not fixture_path.is_file():
            raise ValueError(f"Fixture file is missing: {fixture_path.name}")
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        checksum = canonical_sha256(fixture)
        if fixture.get("fixture_content_sha256") != checksum or row.get("fixture_content_sha256") != checksum:
            raise ValueError(f"Fixture checksum mismatch: {row['fixture_id']}")
        if fixture.get("fixture_id") != row["fixture_id"]:
            raise ValueError(f"Fixture ID mismatch: {row['fixture_id']}")
        if fixture.get("fixture_schema_version") != FIXTURE_SCHEMA_VERSION:
            raise ValueError(f"Fixture schema mismatch: {row['fixture_id']}")
        if fixture.get("fixture_classification") != EVALUATION_ONLY_LABEL:
            raise ValueError(f"Fixture lost evaluation-only classification: {row['fixture_id']}")
        if fixture.get("controlled_change_only") is not True:
            raise ValueError(f"Fixture is not controlled-change-only: {row['fixture_id']}")
        fixture_type = fixture.get("fixture_type", "")
        spec = expected_by_type.get(fixture_type)
        if spec is None:
            raise ValueError(f"Unknown fixture type: {fixture_type}")
        base = fixture.get("base_scenario", {})
        real_base = scenarios.get(base.get("scenario_id", ""))
        if real_base is None:
            raise ValueError(f"Fixture references an unknown base scenario: {row['fixture_id']}")
        for field in BASE_IDENTITY_FIELDS:
            if base.get(field) != real_base.get(field) or row.get(
                {"scenario_id": "base_scenario_id", "site_id": "base_site_id"}.get(field, field)
            ) != base.get(field):
                raise ValueError(f"Fixture base identity mismatch: {row['fixture_id']} / {field}")
        overlay = fixture.get("overlay", {})
        if overlay.get("target_layer") != spec["target_layer"] or overlay.get("field") != spec["field"]:
            raise ValueError(f"Fixture overlay does not match declared type: {row['fixture_id']}")
        if overlay.get("base_value") == overlay.get("counterfactual_value"):
            raise ValueError(f"Fixture has no meaningful mutation: {row['fixture_id']}")
        if overlay["target_layer"] == "regional_operation_plan_item":
            item_id = overlay.get("selector", {}).get("plan_item_id", "")
            item = plan_items.get(item_id)
            if item is None or item.get("scenario_id") != base["scenario_id"]:
                raise ValueError(f"Fixture plan-item selector is invalid: {row['fixture_id']}")
            if item.get(overlay["field"], "") != overlay.get("base_value"):
                raise ValueError(f"Fixture plan-item base value changed: {row['fixture_id']}")
        elif overlay["target_layer"] == "manifest":
            if real_base.get(overlay["field"], "") != overlay.get("base_value"):
                raise ValueError(f"Fixture manifest base value changed: {row['fixture_id']}")
            if len(str(overlay.get("counterfactual_value", ""))) != 64:
                raise ValueError(f"Fixture hash overlay is not SHA-256-shaped: {row['fixture_id']}")
        expected = fixture.get("expected", {})
        if (
            expected.get("a0_status") != spec["expected_a0_status"]
            or expected.get("a5_status") != spec["expected_a5_status"]
            or expected.get("direct_farm_action_issued") is not False
        ):
            raise ValueError(f"Fixture expected outcome is invalid: {row['fixture_id']}")
        type_counts[fixture_type] += 1
        crop_counts[base["crop"]] += 1
        site_counts[base["site_id"]] += 1
        fixtures.append(fixture)
    if type_counts != Counter({spec["fixture_type"]: 10 for spec in FAULT_SPECS}):
        raise ValueError(f"Fixture type coverage mismatch: {dict(type_counts)}")
    if crop_counts != Counter({crop: 10 for crop in FOCUSED_CROPS}):
        raise ValueError(f"Fixture crop coverage mismatch: {dict(crop_counts)}")
    if len(site_counts) != 30 or set(site_counts.values()) != {2}:
        raise ValueError(f"Fixture site coverage mismatch: {dict(site_counts)}")
    return fixtures


def main() -> None:
    fixtures = build_fixtures()
    for fixture in fixtures:
        _write_fixture(FIXTURES_ROOT / f"{fixture['fixture_id']}.json", fixture)
    manifest_rows = []
    for fixture in fixtures:
        base, expected, overlay = fixture["base_scenario"], fixture["expected"], fixture["overlay"]
        manifest_rows.append({
            "fixture_id": fixture["fixture_id"],
            "fixture_schema_version": fixture["fixture_schema_version"],
            "fixture_classification": fixture["fixture_classification"],
            "fixture_family": fixture["fixture_family"],
            "fixture_type": fixture["fixture_type"],
            "target_layer": overlay["target_layer"],
            "base_scenario_id": base["scenario_id"],
            "base_site_id": base["site_id"],
            "crop": base["crop"],
            "state": base["state"],
            "district": base["district"],
            "season": base["season"],
            "decision_date": base["decision_date"],
            "controlled_change_only": "true",
            "expected_a0_status": expected["a0_status"],
            "expected_a5_status": expected["a5_status"],
            "expected_direct_farm_action_issued": "false",
            "fixture_content_sha256": fixture["fixture_content_sha256"],
        })
    write_csv(REGISTRY_ROOT / "provenance_fixture_manifest.csv", MANIFEST_FIELDS, manifest_rows)
    _write_readme()
    _write_data_sources()
    _write_audit(fixtures)
    validate_registry()
    print("Built and validated 60 evaluation-only provenance/alignment fixtures (10 per fault class).")


if __name__ == "__main__":
    main()
