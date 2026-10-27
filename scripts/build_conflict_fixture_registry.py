"""Build the stored evaluation-only provenance-conflict fixture registry.

These records are *not* agricultural observations and must never be admitted
to ``data/registry`` or the frozen 300-scenario benchmark.  Each fixture
references one real, verified base scenario and changes only a declared
provenance/gate property so the deterministic coordinator can be tested under
controlled disagreement.
"""
from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_ROOT = PROJECT_ROOT / "data" / "conflict_fixture_registry"
FIXTURES_ROOT = REGISTRY_ROOT / "fixtures"
SCENARIO_MANIFEST = PROJECT_ROOT / "data" / "scenarios" / "manifests" / "scenario_manifest.csv"
PLAN_ITEMS = PROJECT_ROOT / "data" / "scenarios" / "enriched" / "regional_operation_plan_items.csv"

FIXTURE_SCHEMA_VERSION = "1.0"
EVALUATION_ONLY_LABEL = "evaluation_only_counterfactual_not_real_farm_evidence"
CROPS = ("rice", "wheat", "maize", "chickpea", "soybean", "tomato")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
BASE_IDENTITY_FIELDS = ("scenario_id", "site_id", "crop", "state", "district", "season", "decision_date")

MANIFEST_FIELDS = (
    "fixture_id",
    "fixture_schema_version",
    "fixture_classification",
    "fixture_family",
    "fixture_type",
    "base_scenario_id",
    "base_site_id",
    "crop",
    "state",
    "district",
    "season",
    "decision_date",
    "controlled_change_only",
    "expected_conflict_count",
    "expected_resolution_status",
    "expected_direct_farm_action_issued",
    "fixture_content_sha256",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def canonical_sha256(payload: Mapping[str, Any]) -> str:
    """Hash a fixture independently of its attached content checksum."""
    stable = dict(payload)
    stable.pop("fixture_content_sha256", None)
    canonical = json.dumps(stable, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(canonical.encode("utf-8")).hexdigest()


def choose_base_scenarios() -> dict[str, tuple[dict[str, str], ...]]:
    """Choose one deterministic anchor for each of the five sites per crop."""
    scenarios = read_csv(SCENARIO_MANIFEST)
    bases: dict[str, tuple[dict[str, str], ...]] = {}
    for crop in CROPS:
        by_site: dict[str, list[dict[str, str]]] = {}
        for row in scenarios:
            if row["crop"] == crop:
                by_site.setdefault(row["site_id"], []).append(row)
        if len(by_site) != 5:
            raise ValueError(f"Expected five frozen sites for {crop}, found {len(by_site)}")
        bases[crop] = tuple(
            sorted(rows, key=lambda row: row["scenario_id"])[0]
            for _site_id, rows in sorted(by_site.items())
        )
    return bases


def _first_hash(value: str) -> str | None:
    for candidate in str(value or "").split(";"):
        candidate = candidate.strip()
        if SHA256_RE.fullmatch(candidate):
            return candidate
    return None


def source_by_scenario() -> dict[str, dict[str, str]]:
    """Pick a real plan source to cite as each fixture's immutable base."""
    sources: dict[str, dict[str, str]] = {}
    for item in read_csv(PLAN_ITEMS):
        scenario_id = item["scenario_id"]
        if scenario_id in sources or not item.get("source_document_id"):
            continue
        sources[scenario_id] = {
            "source_document_id": item["source_document_id"],
            "official_url": item.get("source_url", ""),
            "raw_sha256": _first_hash(item.get("source_raw_sha256", "")) or "",
            "locator": item.get("source_location", ""),
        }
    return sources


def real_source(source: Mapping[str, str]) -> dict[str, str | None]:
    return {
        "source_document_id": source["source_document_id"],
        "official_url": source["official_url"] or None,
        "raw_sha256": source["raw_sha256"] or None,
        "locator": source["locator"] or None,
        "source_role": "real_frozen_source_referenced_by_evaluation_fixture",
    }


def overlay_source(source: Mapping[str, str]) -> dict[str, str | None]:
    """Label a controlled overlay without inventing a second external source."""
    return {
        "source_document_id": "EVALUATION_COUNTERFACTUAL_PROVENANCE_OVERLAY",
        "official_url": None,
        "raw_sha256": None,
        "locator": None,
        "source_role": "evaluation_only_counterfactual_provenance_overlay",
    }


def claim(
    *,
    role: str,
    agent_name: str,
    polarity: str,
    target: str,
    source: Mapping[str, str | None],
    source_reference: Mapping[str, str],
    spatial_scope: str,
    temporal_scope: str,
    spatial_rank: int,
    temporal_rank: int,
    source_rank: int,
    disposition: str = "conditional_operation",
    allowed_use: str = "conditional_operation_only",
    gate_result: str = "abstain",
    safety_restriction: bool = False,
    block_reason: str = "evaluation_only_fixture_must_not_issue_direct_farm_action",
) -> dict[str, Any]:
    """Build a non-agronomic claim blueprint for the fixture runner."""
    return {
        "claim_role": role,
        "agent_name": agent_name,
        "decision_domain": "official_operation",
        "disposition": disposition,
        "allowed_use": allowed_use,
        "claim": (
            f"Evaluation-only {polarity} claim for deterministic provenance-conflict testing; "
            "not an agricultural instruction."
        ),
        "summary": "Controlled provenance/gate overlay over a real frozen scenario.",
        "reasoning": (
            "This claim changes only declared evidence scope, validity, provenance, or safety metadata. "
            "It does not add weather, disease, soil, market, maturity, or farm observations."
        ),
        "confidence": 0.5,
        "source": dict(source),
        "spatial_scope": spatial_scope,
        "temporal_scope": temporal_scope,
        "quality": EVALUATION_ONLY_LABEL,
        "gate_result": gate_result,
        "block_reason": block_reason if disposition in {"blocked", "abstain", "no_data"} else None,
        "metadata": {
            "fixture_claim_role": role,
            "fixture_classification": EVALUATION_ONLY_LABEL,
            "base_source_document_id": source_reference["source_document_id"],
            "base_source_raw_sha256": source_reference["raw_sha256"],
            "decision_target": target,
            "assertion_polarity": polarity,
            "resolution_spatial_rank": spatial_rank,
            "resolution_temporal_rank": temporal_rank,
            "resolution_source_rank": source_rank,
            "safety_restriction": safety_restriction,
            "direct_farm_action_issued": False,
        },
    }


def resolution_fixture(
    *,
    fixture_id: str,
    fixture_type: str,
    base: Mapping[str, str],
    source: Mapping[str, str],
) -> dict[str, Any]:
    """Create one deterministic coordinator-resolution fixture."""
    target = f"evaluation_only:{base['scenario_id']}:{fixture_type}"
    real = real_source(source)
    overlay = overlay_source(source)
    district_scope = f"district-scoped evaluation overlay for {base['district']}, {base['state']}"
    state_scope = f"state-scoped evaluation overlay for {base['state']}"
    national_scope = "national evaluation overlay; deliberately broader than the frozen district"
    exact_window = f"exact frozen decision window ending {base['decision_date']}"
    season_window = f"declared {base['season']} seasonal window only"
    expired_window = f"expired controlled window ending before {base['decision_date']}"
    common = {
        "fixture_id": fixture_id,
        "fixture_schema_version": FIXTURE_SCHEMA_VERSION,
        "fixture_classification": EVALUATION_ONLY_LABEL,
        "fixture_family": "coordinator_resolution",
        "fixture_type": fixture_type,
        "base_scenario": {
            key: base[key]
            for key in BASE_IDENTITY_FIELDS
        },
        "controlled_change_only": True,
        "base_source": dict(source),
        "decision_target": target,
        "expected": {
            "conflict_count": 1,
            "direct_farm_action_issued": False,
        },
    }

    if fixture_type == "scope_district_over_state":
        claims = (
            claim(role="preferred", agent_name="fixture_district_source_agent", polarity="supports", target=target,
                  source=real, source_reference=source, spatial_scope=district_scope, temporal_scope=exact_window,
                  spatial_rank=4, temporal_rank=4, source_rank=5),
            claim(role="rejected", agent_name="fixture_state_source_agent", polarity="opposes", target=target,
                  source=overlay, source_reference=source, spatial_scope=state_scope, temporal_scope=exact_window,
                  spatial_rank=3, temporal_rank=4, source_rank=4),
        )
        expected = {"resolution_status": "resolved_by_provenance_precedence", "accepted_roles": ["preferred"], "rejected_roles": ["rejected"]}
    elif fixture_type == "scope_state_over_national":
        claims = (
            claim(role="preferred", agent_name="fixture_state_source_agent", polarity="supports", target=target,
                  source=real, source_reference=source, spatial_scope=state_scope, temporal_scope=exact_window,
                  spatial_rank=3, temporal_rank=4, source_rank=5),
            claim(role="rejected", agent_name="fixture_national_source_agent", polarity="opposes", target=target,
                  source=overlay, source_reference=source, spatial_scope=national_scope, temporal_scope=exact_window,
                  spatial_rank=1, temporal_rank=4, source_rank=4),
        )
        expected = {"resolution_status": "resolved_by_provenance_precedence", "accepted_roles": ["preferred"], "rejected_roles": ["rejected"]}
    elif fixture_type == "temporal_exact_week_over_season":
        claims = (
            claim(role="preferred", agent_name="fixture_exact_week_source_agent", polarity="supports", target=target,
                  source=real, source_reference=source, spatial_scope=district_scope, temporal_scope=exact_window,
                  spatial_rank=4, temporal_rank=4, source_rank=5),
            claim(role="rejected", agent_name="fixture_season_source_agent", polarity="opposes", target=target,
                  source=overlay, source_reference=source, spatial_scope=district_scope, temporal_scope=season_window,
                  spatial_rank=4, temporal_rank=2, source_rank=4),
        )
        expected = {"resolution_status": "resolved_by_provenance_precedence", "accepted_roles": ["preferred"], "rejected_roles": ["rejected"]}
    elif fixture_type == "temporal_current_over_expired":
        claims = (
            claim(role="preferred", agent_name="fixture_current_source_agent", polarity="supports", target=target,
                  source=real, source_reference=source, spatial_scope=district_scope, temporal_scope=exact_window,
                  spatial_rank=4, temporal_rank=4, source_rank=5),
            claim(role="rejected", agent_name="fixture_expired_source_agent", polarity="opposes", target=target,
                  source=overlay, source_reference=source, spatial_scope=district_scope, temporal_scope=expired_window,
                  spatial_rank=4, temporal_rank=1, source_rank=4),
        )
        expected = {"resolution_status": "resolved_by_provenance_precedence", "accepted_roles": ["preferred"], "rejected_roles": ["rejected"]}
    elif fixture_type == "safety_missing_field_condition":
        claims = (
            claim(role="rejected", agent_name="fixture_operation_agent", polarity="supports", target=target,
                  source=real, source_reference=source, spatial_scope=district_scope, temporal_scope=exact_window,
                  spatial_rank=4, temporal_rank=4, source_rank=5),
            claim(role="preferred_safety", agent_name="fixture_field_condition_safety_agent", polarity="opposes", target=target,
                  source=overlay, source_reference=source, spatial_scope=district_scope, temporal_scope=exact_window,
                  spatial_rank=4, temporal_rank=4, source_rank=5, disposition="blocked", allowed_use="unavailable",
                  gate_result="blocked", safety_restriction=True, block_reason="fixture_missing_required_field_condition"),
        )
        expected = {"resolution_status": "resolved_by_safety_restriction", "accepted_roles": ["preferred_safety"], "rejected_roles": ["rejected"]}
    elif fixture_type == "safety_source_restriction":
        claims = (
            claim(role="rejected", agent_name="fixture_operation_agent", polarity="supports", target=target,
                  source=real, source_reference=source, spatial_scope=district_scope, temporal_scope=exact_window,
                  spatial_rank=4, temporal_rank=4, source_rank=5),
            claim(role="preferred_safety", agent_name="fixture_source_safety_agent", polarity="opposes", target=target,
                  source=overlay, source_reference=source, spatial_scope=district_scope, temporal_scope=exact_window,
                  spatial_rank=4, temporal_rank=4, source_rank=5, disposition="blocked", allowed_use="unavailable",
                  gate_result="blocked", safety_restriction=True, block_reason="fixture_source_scope_restriction"),
        )
        expected = {"resolution_status": "resolved_by_safety_restriction", "accepted_roles": ["preferred_safety"], "rejected_roles": ["rejected"]}
    elif fixture_type == "provenance_verified_over_incomplete":
        claims = (
            claim(role="preferred", agent_name="fixture_hash_verified_source_agent", polarity="supports", target=target,
                  source=real, source_reference=source, spatial_scope=district_scope, temporal_scope=exact_window,
                  spatial_rank=4, temporal_rank=4, source_rank=5),
            claim(role="rejected", agent_name="fixture_incomplete_provenance_agent", polarity="opposes", target=target,
                  source=overlay, source_reference=source, spatial_scope=district_scope, temporal_scope=exact_window,
                  spatial_rank=4, temporal_rank=4, source_rank=1),
        )
        expected = {"resolution_status": "resolved_by_provenance_precedence", "accepted_roles": ["preferred"], "rejected_roles": ["rejected"]}
    elif fixture_type == "equal_precedence_safe_defer":
        claims = (
            claim(role="deferred_support", agent_name="fixture_equal_support_agent", polarity="supports", target=target,
                  source=real, source_reference=source, spatial_scope=district_scope, temporal_scope=exact_window,
                  spatial_rank=4, temporal_rank=4, source_rank=5),
            claim(role="deferred_oppose", agent_name="fixture_equal_oppose_agent", polarity="opposes", target=target,
                  source=real, source_reference=source, spatial_scope=district_scope, temporal_scope=exact_window,
                  spatial_rank=4, temporal_rank=4, source_rank=5),
        )
        expected = {"resolution_status": "deferred_equal_precedence", "deferred_roles": ["deferred_support", "deferred_oppose"]}
    else:
        raise ValueError(f"Unknown coordinator fixture type: {fixture_type}")
    common["claims"] = list(claims)
    common["expected"].update(expected)
    common["fixture_content_sha256"] = canonical_sha256(common)
    return common


def integrity_fixture(
    *,
    fixture_id: str,
    base: Mapping[str, str],
    mutation_field: str,
) -> dict[str, Any]:
    """Create a pre-coordinator identity/hash negative fixture."""
    base_value = base[mutation_field]
    if mutation_field == "decision_date":
        controlled_value = "1900-01-01"
    elif mutation_field.endswith("sha256"):
        controlled_value = "0" * 64
    else:
        controlled_value = f"counterfactual_invalid_{mutation_field}"
    fixture = {
        "fixture_id": fixture_id,
        "fixture_schema_version": FIXTURE_SCHEMA_VERSION,
        "fixture_classification": EVALUATION_ONLY_LABEL,
        "fixture_family": "pre_resolution_integrity_rejection",
        "fixture_type": f"wrong_{mutation_field}_blocked_before_coordination",
        "base_scenario": {
            key: base[key]
            for key in BASE_IDENTITY_FIELDS
        },
        "controlled_change_only": True,
        "integrity_overlay": {
            "field": mutation_field,
            "base_value": base_value,
            "counterfactual_value": controlled_value,
            "classification": "controlled_identity_or_hash_mutation_not_real_evidence",
        },
        "expected": {
            "conflict_count": 0,
            "integrity_status": "blocked_before_conflict_detection_and_coordination",
            "direct_farm_action_issued": False,
        },
    }
    fixture["fixture_content_sha256"] = canonical_sha256(fixture)
    return fixture


def negative_control_fixture(
    *,
    fixture_id: str,
    base: Mapping[str, str],
    source: Mapping[str, str],
) -> dict[str, Any]:
    """Store a different-domain pair that must never be called a conflict."""
    fixture = {
        "fixture_id": fixture_id,
        "fixture_schema_version": FIXTURE_SCHEMA_VERSION,
        "fixture_classification": EVALUATION_ONLY_LABEL,
        "fixture_family": "negative_control_no_comparable_conflict",
        "fixture_type": "unrelated_weather_and_market_context_not_conflict",
        "base_scenario": {
            key: base[key]
            for key in BASE_IDENTITY_FIELDS
        },
        "controlled_change_only": True,
        "base_source": dict(source),
        "expected": {
            "conflict_count": 0,
            "direct_farm_action_issued": False,
            "decision_status": "context_only_no_direct_farm_action",
        },
        "claims": [
            {
                "claim_role": "weather_context",
                "agent_name": "fixture_weather_context_agent",
                "decision_domain": "weather_context",
                "disposition": "context",
                "allowed_use": "context_only",
                "claim": "Evaluation-only weather context claim; not an agricultural instruction.",
                "summary": "Controlled non-comparable weather context.",
                "reasoning": "Weather and market are distinct decision domains and must not be manufactured into a conflict.",
                "confidence": 0.5,
                "source": real_source(source),
                "spatial_scope": f"representative-cell context in {base['district']}, {base['state']}",
                "temporal_scope": f"historical frozen decision window ending {base['decision_date']}",
                "quality": EVALUATION_ONLY_LABEL,
                "gate_result": "pass",
                "block_reason": None,
                "metadata": {"fixture_claim_role": "weather_context", "fixture_classification": EVALUATION_ONLY_LABEL},
            },
            {
                "claim_role": "market_context",
                "agent_name": "fixture_market_context_agent",
                "decision_domain": "market_context",
                "disposition": "context",
                "allowed_use": "context_only",
                "claim": "Evaluation-only market context claim; not an agricultural instruction.",
                "summary": "Controlled non-comparable market context.",
                "reasoning": "Historical market context is not an action conflict with weather context.",
                "confidence": 0.5,
                "source": real_source(source),
                "spatial_scope": f"historical nearest-mandi context for {base['district']}, {base['state']}",
                "temporal_scope": f"historical frozen decision window ending {base['decision_date']}",
                "quality": EVALUATION_ONLY_LABEL,
                "gate_result": "pass",
                "block_reason": None,
                "metadata": {"fixture_claim_role": "market_context", "fixture_classification": EVALUATION_ONLY_LABEL},
            },
        ],
    }
    fixture["fixture_content_sha256"] = canonical_sha256(fixture)
    return fixture


def build_fixtures() -> list[dict[str, Any]]:
    """Build exactly ten evaluation cases per focused crop (60 total)."""
    bases, sources = choose_base_scenarios(), source_by_scenario()
    resolver_types = (
        "scope_district_over_state",
        "scope_state_over_national",
        "temporal_exact_week_over_season",
        "temporal_current_over_expired",
        "safety_missing_field_condition",
        "safety_source_restriction",
        "provenance_verified_over_incomplete",
        "equal_precedence_safe_defer",
    )
    integrity_fields = {
        "rice": "crop",
        "wheat": "district",
        "maize": "decision_date",
        "chickpea": "weather_current_response_sha256",
        "soybean": "state",
        "tomato": "market_current_payload_sha256",
    }
    fixtures: list[dict[str, Any]] = []
    for crop in CROPS:
        prefix = f"CF_{crop.upper()}"
        bases_for_crop = bases[crop]
        for index, fixture_type in enumerate(resolver_types, start=1):
            base = bases_for_crop[(index - 1) // 2]
            source = sources.get(base["scenario_id"])
            if source is None:
                raise ValueError(f"No real regional-plan source found for {base['scenario_id']}")
            fixtures.append(resolution_fixture(
                fixture_id=f"{prefix}_{index:02d}_{fixture_type.upper()}",
                fixture_type=fixture_type,
                base=base,
                source=source,
            ))
        base = bases_for_crop[4]
        source = sources.get(base["scenario_id"])
        if source is None:
            raise ValueError(f"No real regional-plan source found for {base['scenario_id']}")
        fixtures.append(integrity_fixture(
            fixture_id=f"{prefix}_09_INTEGRITY_{integrity_fields[crop].upper()}",
            base=base,
            mutation_field=integrity_fields[crop],
        ))
        fixtures.append(negative_control_fixture(
            fixture_id=f"{prefix}_10_NEGATIVE_CONTROL_UNRELATED_DOMAINS",
            base=base,
            source=source,
        ))
    if len(fixtures) != 60:
        raise AssertionError(f"Expected 60 fixtures, built {len(fixtures)}")
    return fixtures


def write_fixture(path: Path, fixture: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fixture, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_audit(fixtures: Sequence[Mapping[str, Any]]) -> None:
    families: dict[str, int] = {}
    crops: dict[str, int] = {}
    sites: dict[str, int] = {}
    for fixture in fixtures:
        families[fixture["fixture_family"]] = families.get(fixture["fixture_family"], 0) + 1
        crop = fixture["base_scenario"]["crop"]
        crops[crop] = crops.get(crop, 0) + 1
        site = fixture["base_scenario"]["site_id"]
        sites[site] = sites.get(site, 0) + 1
    lines = [
        "# Conflict Fixture Registry Audit",
        "",
        f"- Schema version: `{FIXTURE_SCHEMA_VERSION}`",
        f"- Classification: `{EVALUATION_ONLY_LABEL}`",
        "- Frozen 300-scenario manifests and real-site registry: unchanged by this registry.",
        "- Each fixture references a real base scenario and changes only evaluation provenance/gate metadata.",
        "- No fixture contains synthetic weather, soil, disease, fertilizer, market, crop-stage, yield, or farm observation.",
        "- No fixture is loaded by the normal farmer-facing benchmark workflow.",
        "",
        "## Coverage",
        "",
        "| Fixture family | Count |",
        "| --- | ---: |",
        *(f"| {family} | {count} |" for family, count in sorted(families.items())),
        "",
        "| Crop | Stored fixtures |",
        "| --- | ---: |",
        *(f"| {crop} | {crops[crop]} |" for crop in CROPS),
        "",
        f"The registry covers all **{len(sites)} final crop--location sites**, with **two fixtures per site**.",
        "",
        "## Expected resolver behaviour",
        "",
        "- 30 source-scope, temporal-validity, or provenance cases must resolve by deterministic precedence.",
        "- 12 safety cases must resolve by safety restriction and block a direct action.",
        "- 6 equal-precedence cases must defer rather than choose an arbitrary winner.",
        "- 6 integrity overlays must block before conflict detection/coordinator execution.",
        "- 6 unrelated-domain negative controls must not be detected as conflicts.",
        "",
        "The 43 natural NDVI--weather divergence cases remain separate real, non-action benchmark records; they are not copied or relabelled here.",
    ]
    (REGISTRY_ROOT / "CONFLICT_FIXTURE_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_registry(registry_root: Path = REGISTRY_ROOT) -> list[dict[str, Any]]:
    """Fail closed if a stored fixture loses its safety boundary or coverage."""
    manifest_path = registry_root / "conflict_fixture_manifest.csv"
    manifest = read_csv(manifest_path)
    if len(manifest) != 60:
        raise ValueError(f"Expected 60 fixture-manifest rows, found {len(manifest)}")
    fixture_ids = [row["fixture_id"] for row in manifest]
    if len(set(fixture_ids)) != 60:
        raise ValueError("Fixture manifest contains duplicate IDs")
    fixtures: list[dict[str, Any]] = []
    crop_counts = {crop: 0 for crop in CROPS}
    site_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    frozen_scenarios = {row["scenario_id"]: row for row in read_csv(SCENARIO_MANIFEST)}
    for row in manifest:
        path = registry_root / "fixtures" / f"{row['fixture_id']}.json"
        if not path.is_file():
            raise ValueError(f"Fixture file is missing: {path.name}")
        fixture = json.loads(path.read_text(encoding="utf-8"))
        content_sha256 = canonical_sha256(fixture)
        if fixture.get("fixture_content_sha256") != content_sha256:
            raise ValueError(f"Fixture checksum mismatch: {row['fixture_id']}")
        if row.get("fixture_content_sha256") != content_sha256:
            raise ValueError(f"Manifest checksum mismatch: {row['fixture_id']}")
        if fixture.get("fixture_id") != row["fixture_id"]:
            raise ValueError(f"Fixture ID mismatch: {row['fixture_id']}")
        if fixture.get("fixture_schema_version") != FIXTURE_SCHEMA_VERSION:
            raise ValueError(f"Fixture schema mismatch: {row['fixture_id']}")
        if fixture.get("fixture_classification") != EVALUATION_ONLY_LABEL:
            raise ValueError(f"Fixture lost evaluation-only classification: {row['fixture_id']}")
        if fixture.get("controlled_change_only") is not True:
            raise ValueError(f"Fixture is not controlled-change-only: {row['fixture_id']}")
        base = fixture.get("base_scenario", {})
        real_base = frozen_scenarios.get(base.get("scenario_id", ""))
        if real_base is None:
            raise ValueError(f"Fixture references unknown base scenario: {row['fixture_id']}")
        for field in BASE_IDENTITY_FIELDS:
            if base.get(field) != real_base[field]:
                raise ValueError(f"Fixture base identity mismatch for {row['fixture_id']}: {field}")
        for field, manifest_field in (
            ("scenario_id", "base_scenario_id"),
            ("site_id", "base_site_id"),
            ("crop", "crop"),
            ("state", "state"),
            ("district", "district"),
            ("season", "season"),
            ("decision_date", "decision_date"),
        ):
            if row.get(manifest_field) != base.get(field):
                raise ValueError(f"Manifest/base mismatch for {row['fixture_id']}: {manifest_field}")
        crop = base["crop"]
        if crop not in crop_counts:
            raise ValueError(f"Fixture has outside-scope crop: {crop}")
        crop_counts[crop] += 1
        site_counts[base["site_id"]] = site_counts.get(base["site_id"], 0) + 1
        family = fixture["fixture_family"]
        family_counts[family] = family_counts.get(family, 0) + 1
        if family == "coordinator_resolution":
            claims = fixture.get("claims", [])
            if len(claims) != 2:
                raise ValueError(f"Coordinator fixture must contain exactly two claims: {row['fixture_id']}")
            if any(claim.get("quality") != EVALUATION_ONLY_LABEL for claim in claims):
                raise ValueError(f"Coordinator fixture claim lost test-only label: {row['fixture_id']}")
            if any(claim.get("metadata", {}).get("direct_farm_action_issued") is not False for claim in claims):
                raise ValueError(f"Fixture claim could issue a direct action: {row['fixture_id']}")
        elif family == "pre_resolution_integrity_rejection":
            overlay = fixture.get("integrity_overlay", {})
            if not overlay.get("field") or overlay.get("base_value") == overlay.get("counterfactual_value"):
                raise ValueError(f"Integrity fixture has no meaningful controlled mutation: {row['fixture_id']}")
        elif family == "negative_control_no_comparable_conflict":
            domains = {claim.get("decision_domain") for claim in fixture.get("claims", [])}
            if domains != {"weather_context", "market_context"}:
                raise ValueError(f"Negative control must use only unrelated weather/market domains: {row['fixture_id']}")
        else:
            raise ValueError(f"Unknown fixture family: {family}")
        fixtures.append(fixture)
    if any(count != 10 for count in crop_counts.values()):
        raise ValueError(f"Fixture crop coverage must be 10 per crop: {crop_counts}")
    if len(site_counts) != 30 or any(count != 2 for count in site_counts.values()):
        raise ValueError(f"Fixture site coverage must be two per all 30 final sites: {site_counts}")
    expected_families = {
        "coordinator_resolution": 48,
        "pre_resolution_integrity_rejection": 6,
        "negative_control_no_comparable_conflict": 6,
    }
    if family_counts != expected_families:
        raise ValueError(f"Fixture family coverage mismatch: {family_counts}")
    return fixtures


def main() -> None:
    fixtures = build_fixtures()
    for fixture in fixtures:
        write_fixture(FIXTURES_ROOT / f"{fixture['fixture_id']}.json", fixture)
    manifest_rows = []
    for fixture in fixtures:
        base, expected = fixture["base_scenario"], fixture["expected"]
        manifest_rows.append({
            "fixture_id": fixture["fixture_id"],
            "fixture_schema_version": fixture["fixture_schema_version"],
            "fixture_classification": fixture["fixture_classification"],
            "fixture_family": fixture["fixture_family"],
            "fixture_type": fixture["fixture_type"],
            "base_scenario_id": base["scenario_id"],
            "base_site_id": base["site_id"],
            "crop": base["crop"], "state": base["state"], "district": base["district"],
            "season": base["season"], "decision_date": base["decision_date"],
            "controlled_change_only": str(fixture["controlled_change_only"]).lower(),
            "expected_conflict_count": str(expected["conflict_count"]),
            "expected_resolution_status": expected.get("resolution_status", expected.get("integrity_status", "no_conflict_expected")),
            "expected_direct_farm_action_issued": str(expected["direct_farm_action_issued"]).lower(),
            "fixture_content_sha256": fixture["fixture_content_sha256"],
        })
    write_csv(REGISTRY_ROOT / "conflict_fixture_manifest.csv", MANIFEST_FIELDS, manifest_rows)
    write_audit(fixtures)
    validate_registry()
    print("Built and validated 60 evaluation-only conflict fixtures (10 per focused crop).")


if __name__ == "__main__":
    main()
