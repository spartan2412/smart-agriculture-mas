"""Fail-closed loader for the frozen IndiaAgriAlignBench MAS inputs.

This module is intentionally independent of the legacy ``data/loaders.py``.
The legacy loader powers the 22-crop proxy/pilot benchmark; this loader accepts
only one of the 300 source-gated, frozen scenario IDs and validates its linked
registry, scenario, enrichment, RAG-scope, and action-binding evidence.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
IDENTITY_FIELDS = ("crop", "state", "district", "season", "decision_date")


class ScenarioIntegrityError(ValueError):
    """Raised when a frozen benchmark record is missing, inconsistent, or altered."""


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ScenarioIntegrityError(f"Required benchmark artifact is missing: {path}")
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def _index_unique(rows: Sequence[Mapping[str, str]], key: str, label: str) -> dict[str, dict[str, str]]:
    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        value = str(row.get(key, "")).strip()
        if not value:
            raise ScenarioIntegrityError(f"{label} has an empty {key}.")
        if value in indexed:
            raise ScenarioIntegrityError(f"{label} has duplicate {key}: {value}")
        indexed[value] = dict(row)
    return indexed


def _freeze(row: Mapping[str, str]) -> Mapping[str, str]:
    return MappingProxyType(dict(row))


def _payload_hash(path: Path, canonical_json: bool) -> str:
    if canonical_json:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
    return sha256(path.read_bytes()).hexdigest()


def _canonical_row_hash(row: Mapping[str, str], digest_field: str) -> str:
    """Return the canonical digest used by the regional-plan artifacts."""
    payload = {field: row.get(field, "") for field in row if field != digest_field}
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class ScenarioIdentity:
    scenario_id: str
    site_id: str
    crop: str
    state: str
    district: str
    season: str
    decision_date: str
    decision_window_utc: str
    geometry_scope: str


@dataclass(frozen=True)
class FrozenBenchmarkScenario:
    """The only input bundle future benchmark agents may consume."""

    identity: ScenarioIdentity
    manifest: Mapping[str, str]
    registry_site: Mapping[str, str]
    registry_admission: Mapping[str, str]
    representative_cell: Mapping[str, str]
    registry_weather: Mapping[str, str]
    registry_soil_profile: Tuple[Mapping[str, str], ...]
    registry_sentinel: Mapping[str, str]
    registry_crop_season: Mapping[str, str]
    registry_market: Mapping[str, str]
    management_bundle: Mapping[str, str]
    features: Mapping[str, str]
    evidence_status: Mapping[str, str]
    capability_contract: Mapping[str, str]
    regional_calendar: Mapping[str, str]
    management_policy: Mapping[str, str]
    regional_policy_detail_cards: Tuple[Mapping[str, str], ...]
    regional_operation_plan_summary: Mapping[str, str]
    regional_operation_plan_items: Tuple[Mapping[str, str], ...]
    regional_operation_plan_provenance: Tuple[Mapping[str, str], ...]
    water_context_features: Mapping[str, str]
    water_context_status: Mapping[str, str]
    satellite_context_manifest: Mapping[str, str]
    satellite_context_features: Optional[Mapping[str, str]]
    satellite_context_status: Mapping[str, str]
    satellite_recovery_features: Optional[Mapping[str, str]]
    satellite_recovery_status: Optional[Mapping[str, str]]
    market_context_features: Mapping[str, str]
    market_context_status: Mapping[str, str]
    market_context_manifest: Mapping[str, str]
    market_recovery_feasibility: Optional[Mapping[str, str]]
    rag_scope: Tuple[Mapping[str, str], ...]
    retrievable_rag_chunks: Tuple[Mapping[str, str], ...]
    retrievable_operation_passages: Tuple[Mapping[str, str], ...]
    recovered_operation_sources: Tuple[Mapping[str, str], ...]
    action_records: Tuple[Mapping[str, str], ...]
    action_bindings: Tuple[Mapping[str, str], ...]
    exact_week_action_records: Tuple[Mapping[str, str], ...]
    exact_week_action_bindings: Tuple[Mapping[str, str], ...]
    ndvi_timeseries_features: Mapping[str, str]
    ndvi_timeseries_status: Mapping[str, str]
    ndvi_timeseries_observations: Tuple[Mapping[str, str], ...]
    natural_signal_divergence: Optional[Mapping[str, str]]
    public_district_kvk_advisory_status: Mapping[str, str]
    archived_advisory_status: Mapping[str, str]
    archived_advisory_bindings: Tuple[Mapping[str, str], ...]
    postharvest_logistics_context: Mapping[str, str]
    postharvest_handling_profile: Mapping[str, str]
    postharvest_plan_items: Tuple[Mapping[str, str], ...]
    postharvest_site_summary: Mapping[str, str]
    postharvest_site_facility_context: Tuple[Mapping[str, str], ...]
    postharvest_static_route_context: Tuple[Mapping[str, str], ...]
    postharvest_state_infrastructure: Tuple[Mapping[str, str], ...]
    postharvest_rag_scope: Tuple[Mapping[str, str], ...]
    retrievable_postharvest_rag_passages: Tuple[Mapping[str, str], ...]
    postharvest_source_inventory: Tuple[Mapping[str, str], ...]
    postharvest_logistics_provenance: Tuple[Mapping[str, str], ...]

    def agent_permission(self, contract_field: str) -> str:
        """Return one machine-readable capability decision from the frozen contract."""
        if contract_field not in self.capability_contract:
            raise KeyError(f"Unknown capability-contract field: {contract_field}")
        return self.capability_contract[contract_field]


class FrozenBenchmarkLoader:
    """Load and validate the benchmark once, then serve immutable scenario bundles."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = Path(project_root or PROJECT_ROOT).resolve()
        self.registry_root = self.project_root / "data" / "registry"
        self.scenario_root = self.project_root / "data" / "scenarios"
        self.enriched_root = self.scenario_root / "enriched"
        self._loaded = False

    def scenario_ids(self) -> Tuple[str, ...]:
        self._ensure_loaded()
        return tuple(sorted(self._manifest))

    def load(self, scenario_id: str, *, verify_raw_hashes: bool = True) -> FrozenBenchmarkScenario:
        self._ensure_loaded()
        if scenario_id not in self._manifest:
            raise ScenarioIntegrityError(f"Unknown frozen scenario_id: {scenario_id}")
        manifest = self._manifest[scenario_id]
        identity = ScenarioIdentity(
            scenario_id=scenario_id,
            site_id=manifest["site_id"],
            crop=manifest["crop"],
            state=manifest["state"],
            district=manifest["district"],
            season=manifest["season"],
            decision_date=manifest["decision_date"],
            decision_window_utc=manifest["decision_window_utc"],
            geometry_scope=manifest["geometry_scope"],
        )
        rag_scope = self._rag_scope[scenario_id]
        retrievable_source_ids = [
            row["source_document_id"]
            for row in rag_scope
            if row["rag_scope_status"].startswith("admitted_")
        ]
        action_bindings = self._action_bindings[scenario_id]
        exact_week_bindings = self._exact_week_bindings[scenario_id]
        plan_items = self._regional_operation_plan_items[scenario_id]
        postharvest_plan_items = self._postharvest_plan_items[scenario_id]
        postharvest_rag_scope = self._postharvest_rag_scope[scenario_id]
        postharvest_passage_ids = tuple(row["passage_id"] for row in postharvest_rag_scope)
        postharvest_context = self._postharvest_logistics_context[scenario_id]
        postharvest_site_summary = self._postharvest_site_summary[manifest["site_id"]]
        operation_passages = tuple(
            row
            for row in plan_items
            if row.get("plan_item_type") == "time_valid_source_quoted_conditional_operation"
        )
        recovered_source_ids = tuple(sorted({
            row["source_document_id"]
            for row in operation_passages
            if row.get("source_document_id") in self._recovered_operation_sources
        }))
        if verify_raw_hashes:
            self._verify_scenario_payloads(manifest)
            self._verify_satellite_context_payload(self._satellite_context_manifest[scenario_id])
            self._verify_recovered_operation_sources(recovered_source_ids)
            self._verify_postharvest_sources(
                tuple(sorted({row["source_document_id"] for row in postharvest_plan_items}))
            )
        return FrozenBenchmarkScenario(
            identity=identity,
            manifest=_freeze(manifest),
            registry_site=_freeze(self._sites[manifest["site_id"]]),
            registry_admission=_freeze(self._admissions[manifest["site_id"]]),
            representative_cell=_freeze(self._representative_cells[manifest["site_id"]]),
            registry_weather=_freeze(self._registry_weather[manifest["site_id"]]),
            registry_soil_profile=tuple(_freeze(row) for row in self._registry_soil[manifest["site_id"]]),
            registry_sentinel=_freeze(self._preflight_sentinel[manifest["site_id"]]),
            registry_crop_season=_freeze(self._registry_crop_season[manifest["site_id"]]),
            registry_market=_freeze(self._registry_market[manifest["site_id"]]),
            management_bundle=_freeze(self._management_bundles[manifest["management_bundle_id"]]),
            features=_freeze(self._features[scenario_id]),
            evidence_status=_freeze(self._evidence[scenario_id]),
            capability_contract=_freeze(self._contract[scenario_id]),
            regional_calendar=_freeze(self._regional_calendar[scenario_id]),
            management_policy=_freeze(self._management_policy[scenario_id]),
            regional_policy_detail_cards=tuple(
                _freeze(row) for row in self._regional_policy_detail_cards[manifest["management_bundle_id"]]
            ),
            regional_operation_plan_summary=_freeze(self._regional_operation_plan_summary[scenario_id]),
            regional_operation_plan_items=tuple(_freeze(row) for row in plan_items),
            regional_operation_plan_provenance=tuple(_freeze(row) for row in self._regional_operation_plan_provenance),
            water_context_features=_freeze(self._water_features[scenario_id]),
            water_context_status=_freeze(self._water_status[scenario_id]),
            satellite_context_manifest=_freeze(self._satellite_context_manifest[scenario_id]),
            satellite_context_features=(
                _freeze(self._satellite_features[scenario_id]) if scenario_id in self._satellite_features else None
            ),
            satellite_context_status=_freeze(self._satellite_status[scenario_id]),
            satellite_recovery_features=(
                _freeze(self._satellite_recovery_features[scenario_id])
                if scenario_id in self._satellite_recovery_features else None
            ),
            satellite_recovery_status=(
                _freeze(self._satellite_recovery_status[scenario_id])
                if scenario_id in self._satellite_recovery_status else None
            ),
            market_context_features=_freeze(self._market_features[scenario_id]),
            market_context_status=_freeze(self._market_status[scenario_id]),
            market_context_manifest=_freeze(self._market_context_manifest[scenario_id]),
            market_recovery_feasibility=(
                _freeze(self._market_recovery[scenario_id]) if scenario_id in self._market_recovery else None
            ),
            rag_scope=tuple(_freeze(row) for row in rag_scope),
            retrievable_rag_chunks=tuple(
                _freeze(chunk)
                for source_document_id in retrievable_source_ids
                for chunk in self._rag_chunks[source_document_id]
            ),
            retrievable_operation_passages=tuple(_freeze(row) for row in operation_passages),
            recovered_operation_sources=tuple(
                _freeze(self._recovered_operation_sources[source_id]) for source_id in recovered_source_ids
            ),
            action_records=tuple(_freeze(self._actions[row["action_id"]]) for row in action_bindings),
            action_bindings=tuple(_freeze(row) for row in action_bindings),
            exact_week_action_records=tuple(
                _freeze(self._exact_week_actions[row["action_id"]]) for row in exact_week_bindings
            ),
            exact_week_action_bindings=tuple(_freeze(row) for row in exact_week_bindings),
            ndvi_timeseries_features=_freeze(self._ndvi_timeseries_features[scenario_id]),
            ndvi_timeseries_status=_freeze(self._ndvi_timeseries_status[scenario_id]),
            ndvi_timeseries_observations=tuple(
                _freeze(row) for row in self._ndvi_timeseries_observations.get(scenario_id, [])
            ),
            natural_signal_divergence=(
                _freeze(self._natural_divergence[scenario_id]) if scenario_id in self._natural_divergence else None
            ),
            public_district_kvk_advisory_status=_freeze(self._district_kvk_status[scenario_id]),
            archived_advisory_status=_freeze(self._archived_advisory_status[scenario_id]),
            archived_advisory_bindings=tuple(
                _freeze(row) for row in self._archived_advisory_bindings[scenario_id]
            ),
            postharvest_logistics_context=_freeze(postharvest_context),
            postharvest_handling_profile=_freeze(
                self._postharvest_handling_profiles[postharvest_context["profile_id"]]
            ),
            postharvest_plan_items=tuple(_freeze(row) for row in postharvest_plan_items),
            postharvest_site_summary=_freeze(postharvest_site_summary),
            postharvest_site_facility_context=tuple(
                _freeze(row) for row in self._postharvest_site_facility_context[manifest["site_id"]]
            ),
            postharvest_static_route_context=tuple(
                _freeze(row) for row in self._postharvest_static_route_context.get(manifest["site_id"], [])
            ),
            postharvest_state_infrastructure=tuple(
                _freeze(row) for row in self._postharvest_state_infrastructure.get(manifest["state"], [])
            ),
            postharvest_rag_scope=tuple(_freeze(row) for row in postharvest_rag_scope),
            retrievable_postharvest_rag_passages=tuple(
                _freeze(self._postharvest_rag_passages[passage_id]) for passage_id in postharvest_passage_ids
            ),
            postharvest_source_inventory=tuple(
                _freeze(row) for _, row in sorted(self._postharvest_source_inventory.items())
            ),
            postharvest_logistics_provenance=tuple(
                _freeze(row) for row in self._postharvest_logistics_provenance
            ),
        )

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._sites = _index_unique(_read_csv(self.registry_root / "final_study_sites.csv"), "site_id", "final study sites")
        self._admissions = _index_unique(
            _read_csv(self.registry_root / "source_scoped_final_site_admission.csv"), "site_id", "site admissions"
        )
        self._representative_cells = _index_unique(
            _read_csv(self.registry_root / "preflight_representative_cropland_cells.csv"), "site_id", "representative cells"
        )
        self._registry_weather = _index_unique(
            _read_csv(self.registry_root / "preflight_nasa_power_fixed_window_weather.csv"), "site_id", "registry weather"
        )
        self._registry_soil = self._group_by(
            _read_csv(self.registry_root / "preflight_soilgrids_wcs_profiles.csv"), "site_id", "registry SoilGrids profiles"
        )
        self._preflight_sentinel = _index_unique(
            _read_csv(self.registry_root / "preflight_sentinel_scene_coverage.csv"), "site_id", "registry Sentinel coverage"
        )
        self._registry_crop_season = _index_unique(
            _read_csv(self.registry_root / "preflight_icar_crida_ccp_coverage.csv"), "site_id", "registry crop-season evidence"
        )
        self._registry_market = _index_unique(
            _read_csv(self.registry_root / "preflight_agmarknet_historical_market_coverage.csv"), "site_id", "registry market evidence"
        )
        self._management_bundles = _index_unique(
            _read_csv(self.registry_root / "preflight_management_bundle_catalog.csv"), "management_bundle_id", "management bundles"
        )
        self._manifest = _index_unique(
            _read_csv(self.scenario_root / "manifests" / "scenario_manifest.csv"), "scenario_id", "scenario manifest"
        )
        self._features = _index_unique(
            _read_csv(self.scenario_root / "processed" / "scenario_features.csv"), "scenario_id", "scenario features"
        )
        self._evidence = _index_unique(
            _read_csv(self.scenario_root / "evidence" / "scenario_evidence_status.csv"), "scenario_id", "scenario evidence status"
        )
        self._contract = _index_unique(
            _read_csv(self.enriched_root / "mas_enrichment_contract.csv"), "scenario_id", "MAS capability contract"
        )
        self._regional_calendar = _index_unique(
            _read_csv(self.enriched_root / "regional_calendar_features.csv"), "scenario_id", "regional calendar features"
        )
        self._management_policy = _index_unique(
            _read_csv(self.enriched_root / "management_policy_features.csv"), "scenario_id", "management policy features"
        )
        self._regional_policy_detail_cards = self._group_by(
            _read_csv(self.enriched_root / "regional_policy_detail_cards.csv"),
            "management_bundle_id",
            "regional policy detail cards",
        )
        self._regional_operation_plan_summary = _index_unique(
            _read_csv(self.enriched_root / "regional_operation_plan_summary.csv"),
            "scenario_id",
            "regional operation-plan summaries",
        )
        self._regional_operation_plan_items = self._group_rows(
            _read_csv(self.enriched_root / "regional_operation_plan_items.csv"),
            "regional operation-plan items",
        )
        self._regional_operation_plan_provenance = _read_csv(
            self.enriched_root / "regional_operation_plan_provenance.csv"
        )
        self._water_features = _index_unique(
            _read_csv(self.enriched_root / "nasa_power_water_context_features.csv"), "scenario_id", "water context features"
        )
        self._water_status = _index_unique(
            _read_csv(self.enriched_root / "nasa_power_water_context_status.csv"), "scenario_id", "water context status"
        )
        self._satellite_features = _index_unique(
            _read_csv(self.enriched_root / "sentinel_ndvi_context_features.csv"), "scenario_id", "satellite context features"
        )
        self._satellite_context_manifest = _index_unique(
            _read_csv(self.enriched_root / "sentinel_ndvi_context_manifest.csv"),
            "scenario_id",
            "satellite context source manifests",
        )
        self._satellite_status = _index_unique(
            _read_csv(self.enriched_root / "sentinel_ndvi_context_status.csv"), "scenario_id", "satellite context status"
        )
        self._satellite_recovery_features = _index_unique(
            _read_csv(self.enriched_root / "sentinel_ndvi_recovery_features.csv"), "scenario_id", "satellite recovery features"
        )
        self._satellite_recovery_status = _index_unique(
            _read_csv(self.enriched_root / "sentinel_ndvi_recovery_status.csv"), "scenario_id", "satellite recovery status"
        )
        self._verified_satellite_context_payloads: set[str] = set()
        self._market_features = _index_unique(
            _read_csv(self.enriched_root / "agmarknet_embedded_market_context_features.csv"), "scenario_id", "market context features"
        )
        self._market_status = _index_unique(
            _read_csv(self.enriched_root / "agmarknet_embedded_market_context_status.csv"), "scenario_id", "market context status"
        )
        self._market_context_manifest = _index_unique(
            _read_csv(self.enriched_root / "agmarknet_embedded_market_context_manifest.csv"),
            "scenario_id",
            "market context source manifests",
        )
        self._market_recovery = _index_unique(
            _read_csv(self.enriched_root / "market_recovery_feasibility.csv"), "scenario_id", "market recovery feasibility"
        )
        self._rag_documents = _index_unique(
            _read_csv(self.enriched_root / "official_rag_corpus_catalog.csv"), "source_document_id", "official RAG catalog"
        )
        self._rag_chunks = self._group_by(
            _read_csv(self.enriched_root / "official_rag_corpus_all_chunks.csv"), "source_document_id", "official RAG chunks"
        )
        self._actions = _index_unique(
            _read_csv(self.enriched_root / "official_action_records_all.csv"), "action_id", "official action catalog"
        )
        self._rag_scope = self._group_rows(
            _read_csv(self.enriched_root / "scenario_official_rag_scope_all.csv"), "RAG scope"
        )
        self._action_bindings = self._group_rows(
            _read_csv(self.enriched_root / "scenario_official_action_bindings_all.csv"), "action bindings"
        )
        recovery_rows = [
            *_read_csv(self.enriched_root / "archived_pau_kharif_source_inventory.csv"),
            *_read_csv(self.enriched_root / "archived_pau_rabi_source_inventory.csv"),
            *_read_csv(self.enriched_root / "mpkv_chickpea_source_inventory.csv"),
        ]
        self._recovered_operation_sources = _index_unique(
            recovery_rows, "source_document_id", "recovered operation-source inventory"
        )
        self._verified_recovered_operation_sources: set[str] = set()
        self._exact_week_actions = _index_unique(
            _read_csv(self.enriched_root / "exact_week_iisr_action_records.csv"), "action_id", "exact-week action catalog"
        )
        self._exact_week_bindings = self._group_rows(
            _read_csv(self.enriched_root / "scenario_exact_week_iisr_action_bindings.csv"), "exact-week action bindings"
        )
        self._ndvi_timeseries_features = _index_unique(
            _read_csv(self.enriched_root / "sentinel_ndvi_timeseries_features.csv"), "scenario_id", "NDVI timeseries features"
        )
        self._ndvi_timeseries_status = _index_unique(
            _read_csv(self.enriched_root / "sentinel_ndvi_timeseries_status.csv"), "scenario_id", "NDVI timeseries status"
        )
        self._ndvi_timeseries_observations = self._group_rows(
            _read_csv(self.enriched_root / "sentinel_ndvi_timeseries_observations.csv"), "NDVI timeseries observations"
        )
        self._natural_divergence = _index_unique(
            _read_csv(self.enriched_root / "natural_signal_divergence_candidates.csv"), "scenario_id", "natural signal divergence"
        )
        self._district_kvk_status = _index_unique(
            _read_csv(self.enriched_root / "scenario_public_district_kvk_advisory_status.csv"), "scenario_id", "district KVK advisory status"
        )
        self._archived_advisory_status = _index_unique(
            _read_csv(self.enriched_root / "scenario_archived_advisory_status.csv"), "scenario_id", "archived advisory status"
        )
        self._archived_advisory_bindings = self._group_rows(
            _read_csv(self.enriched_root / "scenario_archived_advisory_bindings.csv"), "archived advisory bindings"
        )
        self._postharvest_source_inventory = _index_unique(
            _read_csv(self.enriched_root / "postharvest_source_inventory.csv"),
            "source_document_id",
            "postharvest source inventory",
        )
        self._verified_postharvest_sources: set[str] = set()
        self._postharvest_handling_profiles = _index_unique(
            _read_csv(self.enriched_root / "postharvest_handling_profiles.csv"),
            "profile_id",
            "postharvest handling profiles",
        )
        self._postharvest_operation_library = _index_unique(
            _read_csv(self.enriched_root / "postharvest_operation_library.csv"),
            "operation_id",
            "postharvest operation library",
        )
        self._postharvest_logistics_context = _index_unique(
            _read_csv(self.enriched_root / "scenario_postharvest_logistics_context.csv"),
            "scenario_id",
            "postharvest logistics context",
        )
        self._postharvest_plan_items = self._group_rows(
            _read_csv(self.enriched_root / "scenario_postharvest_plan_items.csv"),
            "postharvest plan items",
        )
        self._postharvest_site_summary = _index_unique(
            _read_csv(self.enriched_root / "postharvest_site_summary.csv"),
            "site_id",
            "postharvest site summaries",
        )
        self._postharvest_site_facility_context = self._group_by(
            _read_csv(self.enriched_root / "postharvest_site_facility_context.csv"),
            "site_id",
            "postharvest site facility context",
        )
        self._postharvest_static_route_context = self._group_by(
            _read_csv(self.enriched_root / "postharvest_static_route_context.csv"),
            "site_id",
            "postharvest static route context",
        )
        self._postharvest_state_infrastructure = self._group_by(
            _read_csv(self.enriched_root / "postharvest_nhb_state_infrastructure.csv"),
            "state",
            "postharvest state infrastructure",
        )
        self._postharvest_rag_passages = _index_unique(
            _read_csv(self.enriched_root / "postharvest_rag_passages.csv"),
            "passage_id",
            "postharvest RAG passages",
        )
        self._postharvest_rag_scope = self._group_rows(
            _read_csv(self.enriched_root / "scenario_postharvest_rag_scope.csv"),
            "postharvest RAG scope",
        )
        self._postharvest_nhb_facilities = _index_unique(
            _read_csv(self.enriched_root / "postharvest_nhb_facility_records.csv"),
            "facility_id",
            "postharvest NHB facility records",
        )
        self._postharvest_wdra_warehouses = _index_unique(
            _read_csv(self.enriched_root / "postharvest_wdra_warehouse_records.csv"),
            "warehouse_id",
            "postharvest WDRA warehouse records",
        )
        self._postharvest_logistics_provenance = _read_csv(
            self.enriched_root / "postharvest_logistics_provenance.csv"
        )
        self._validate_dataset()
        self._loaded = True

    def _group_rows(self, rows: Iterable[Mapping[str, str]], label: str) -> dict[str, list[dict[str, str]]]:
        return self._group_by(rows, "scenario_id", label)

    @staticmethod
    def _group_by(
        rows: Iterable[Mapping[str, str]], key: str, label: str
    ) -> dict[str, list[dict[str, str]]]:
        grouped: dict[str, list[dict[str, str]]] = {}
        for row in rows:
            value = str(row.get(key, "")).strip()
            if not value:
                raise ScenarioIntegrityError(f"{label} contains a row without {key}.")
            grouped.setdefault(value, []).append(dict(row))
        return grouped

    def _validate_dataset(self) -> None:
        scenario_ids = set(self._manifest)
        if len(scenario_ids) != 300:
            raise ScenarioIntegrityError(f"Expected exactly 300 frozen scenarios, found {len(scenario_ids)}.")
        site_ids = set(self._sites)
        if len(site_ids) != 30:
            raise ScenarioIntegrityError(f"Expected exactly 30 admitted final sites, found {len(site_ids)}.")
        for label, indexed in (
            ("site admissions", self._admissions),
            ("representative cells", self._representative_cells),
            ("registry weather", self._registry_weather),
            ("registry Sentinel", self._preflight_sentinel),
            ("registry crop-season evidence", self._registry_crop_season),
            ("registry market evidence", self._registry_market),
        ):
            if set(indexed) != site_ids:
                raise ScenarioIntegrityError(f"{label} does not have exact one-to-one final-site coverage.")
        if set(self._registry_soil) != site_ids or any(len(rows) != 6 for rows in self._registry_soil.values()):
            raise ScenarioIntegrityError("Registry SoilGrids profiles do not provide six rows for every final site.")
        for label, indexed in (
            ("features", self._features),
            ("evidence status", self._evidence),
            ("capability contract", self._contract),
            ("regional calendar", self._regional_calendar),
            ("management policy", self._management_policy),
            ("regional operation-plan summary", self._regional_operation_plan_summary),
            ("water context features", self._water_features),
            ("water context status", self._water_status),
            ("satellite context status", self._satellite_status),
            ("satellite context source manifests", self._satellite_context_manifest),
            ("market context features", self._market_features),
            ("market context status", self._market_status),
            ("market context source manifests", self._market_context_manifest),
            ("NDVI timeseries features", self._ndvi_timeseries_features),
            ("NDVI timeseries status", self._ndvi_timeseries_status),
            ("district KVK status", self._district_kvk_status),
            ("archived advisory status", self._archived_advisory_status),
            ("postharvest logistics context", self._postharvest_logistics_context),
        ):
            if set(indexed) != scenario_ids:
                raise ScenarioIntegrityError(f"{label} does not have exact one-to-one scenario coverage.")
        for label, grouped in (
            ("RAG scope", self._rag_scope),
            ("action bindings", self._action_bindings),
            ("regional operation-plan items", self._regional_operation_plan_items),
            ("exact-week action bindings", self._exact_week_bindings),
            ("archived advisory bindings", self._archived_advisory_bindings),
            ("postharvest plan items", self._postharvest_plan_items),
            ("postharvest RAG scope", self._postharvest_rag_scope),
        ):
            if set(grouped) != scenario_ids:
                raise ScenarioIntegrityError(f"{label} does not cover every frozen scenario.")
        for label, indexed in (
            ("satellite context features", self._satellite_features),
            ("satellite recovery features", self._satellite_recovery_features),
            ("satellite recovery status", self._satellite_recovery_status),
            ("market recovery feasibility", self._market_recovery),
            ("natural signal divergence", self._natural_divergence),
        ):
            if not set(indexed).issubset(scenario_ids):
                raise ScenarioIntegrityError(f"{label} references an unknown frozen scenario.")
        if set(self._satellite_recovery_features) != set(self._satellite_recovery_status):
            raise ScenarioIntegrityError("Satellite recovery features and statuses have different scenario coverage.")
        if set(self._rag_chunks) != set(self._rag_documents):
            raise ScenarioIntegrityError("Official RAG chunks do not cover every admitted source document.")
        if set(self._postharvest_site_summary) != site_ids:
            raise ScenarioIntegrityError("Postharvest site summaries do not have exact final-site coverage.")
        if set(self._regional_policy_detail_cards) != set(self._management_bundles):
            raise ScenarioIntegrityError(
                "Regional policy detail cards do not have exact management-bundle coverage."
            )
        for bundle_id, bundle in self._management_bundles.items():
            cards = self._regional_policy_detail_cards[bundle_id]
            expected_sources = {
                "fertilizer": bundle.get("fertilizer_source_id", ""),
                "crop_protection": bundle.get("protection_source_id", ""),
            }
            cards_by_domain = {row.get("policy_domain", ""): row for row in cards}
            if set(cards_by_domain) != set(expected_sources) or len(cards_by_domain) != len(cards):
                raise ScenarioIntegrityError(
                    f"{bundle_id} must contain one nutrient and one crop-protection policy detail card."
                )
            for domain, source_id in expected_sources.items():
                card = cards_by_domain[domain]
                if (
                    card.get("source_document_id") != source_id
                    or card.get("record_status") != "verified_source_recorded_regional_policy_detail"
                    or not card.get("detail_text")
                    or not card.get("applicability_conditions")
                    or not card.get("non_action_boundary")
                ):
                    raise ScenarioIntegrityError(
                        f"{bundle_id} {domain} policy detail card is incomplete or mismatched."
                    )
        if set(self._postharvest_site_facility_context) != site_ids:
            raise ScenarioIntegrityError("Postharvest facility context does not have exact final-site coverage.")
        if not set(self._postharvest_static_route_context).issubset(site_ids):
            raise ScenarioIntegrityError("Postharvest static routes reference an unknown final site.")
        benchmark_states = {row["state"] for row in self._manifest.values()}
        if not benchmark_states.issubset(self._postharvest_state_infrastructure):
            raise ScenarioIntegrityError("Postharvest state infrastructure is missing a benchmark state.")
        self._validate_postharvest_global_rows(benchmark_states)
        expected_plan_provenance = {
            "frozen_scenario_manifest",
            "regional_calendar_features",
            "management_policy_features",
            "official_action_records",
            "scenario_official_action_bindings",
        }
        plan_provenance = {row.get("artifact_role", ""): row for row in self._regional_operation_plan_provenance}
        if set(plan_provenance) != expected_plan_provenance or len(plan_provenance) != len(self._regional_operation_plan_provenance):
            raise ScenarioIntegrityError("Regional operation-plan provenance is incomplete or duplicated.")
        for role, row in plan_provenance.items():
            relative = row.get("input_path", "")
            path = (self.project_root / relative).resolve()
            if self.project_root not in path.parents or not path.is_file():
                raise ScenarioIntegrityError(f"Regional operation-plan provenance path is invalid for {role}.")
            if _payload_hash(path, False) != row.get("input_sha256", ""):
                raise ScenarioIntegrityError(f"Regional operation-plan provenance hash mismatch for {role}.")
        for scenario_id, manifest in self._manifest.items():
            self._validate_manifest_identity(scenario_id, manifest)
            self._validate_core_rows(scenario_id, manifest)
            self._validate_enrichment_rows(scenario_id, manifest)
            self._validate_rag_rows(scenario_id, manifest)
            self._validate_action_rows(scenario_id, manifest)
            self._validate_regional_operation_plan_rows(scenario_id, manifest)
            self._validate_postharvest_rows(scenario_id, manifest)

    def _validate_manifest_identity(self, scenario_id: str, manifest: Mapping[str, str]) -> None:
        required = ("site_id", "crop", "state", "district", "season", "decision_date", "decision_window_utc", "geometry_scope")
        if any(not manifest.get(field) for field in required):
            raise ScenarioIntegrityError(f"{scenario_id} has incomplete identity fields.")
        try:
            decision_date = date.fromisoformat(manifest["decision_date"])
        except ValueError as error:
            raise ScenarioIntegrityError(f"{scenario_id} has an invalid decision date.") from error
        site_id = manifest["site_id"]
        if site_id not in self._sites or site_id not in self._admissions:
            raise ScenarioIntegrityError(f"{scenario_id} references an unregistered site: {site_id}")
        site, admission = self._sites[site_id], self._admissions[site_id]
        if site.get("freeze_status") != "admitted" or admission.get("admission_status") != "admitted":
            raise ScenarioIntegrityError(f"{scenario_id} references a site that is not admitted.")
        for manifest_field, site_field in (("crop", "crop"), ("state", "state"), ("district", "district"), ("season", "proposed_season"), ("season_window", "season_window"), ("geometry_scope", "geometry_scope"), ("management_bundle_id", "management_bundle_id"), ("fertilizer_source_id", "fertilizer_source_id"), ("protection_source_id", "protection_source_id")):
            if manifest.get(manifest_field) != site.get(site_field):
                raise ScenarioIntegrityError(f"{scenario_id} does not match frozen site field {manifest_field}.")
        for coordinate in ("longitude", "latitude"):
            if abs(float(manifest[coordinate]) - float(site[coordinate])) > 0.00001:
                raise ScenarioIntegrityError(f"{scenario_id} does not match frozen site {coordinate}.")
        if not self._month_in_window(decision_date.month, manifest["season_window"]):
            raise ScenarioIntegrityError(f"{scenario_id} decision date falls outside its declared season window.")
        if manifest.get("scenario_type") == "verified_anchor_context" and manifest["decision_date"] != site["fixed_decision_date"]:
            raise ScenarioIntegrityError(f"{scenario_id} anchor date differs from its frozen site date.")

    @staticmethod
    def _month_in_window(month: int, window: str) -> bool:
        month_names = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
        try:
            start_name, end_name = window.split("-", 1)
            start, end = month_names[start_name], month_names[end_name]
        except (KeyError, ValueError) as error:
            raise ScenarioIntegrityError(f"Unsupported season window: {window}") from error
        return start <= month <= end if start <= end else month >= start or month <= end

    def _validate_core_rows(self, scenario_id: str, manifest: Mapping[str, str]) -> None:
        feature, evidence, contract = self._features[scenario_id], self._evidence[scenario_id], self._contract[scenario_id]
        for field in ("satellite_item_id", "satellite_datetime_utc"):
            if feature.get(field) != manifest.get(field):
                raise ScenarioIntegrityError(f"{scenario_id} feature {field} differs from manifest.")
        for field in ("crop_stage_status", "disease_event_status", "farm_fertilizer_status", "crop_protection_status"):
            if evidence.get(field) != manifest.get(field):
                raise ScenarioIntegrityError(f"{scenario_id} evidence {field} differs from manifest.")
        if evidence.get("fertilizer_source_id") != manifest.get("fertilizer_source_id") or evidence.get("protection_source_id") != manifest.get("protection_source_id"):
            raise ScenarioIntegrityError(f"{scenario_id} management source IDs differ between manifest and evidence.")
        if contract.get("crop_stage_agent") != manifest.get("crop_stage_status") or contract.get("disease_diagnosis_agent") != manifest.get("disease_event_status"):
            raise ScenarioIntegrityError(f"{scenario_id} capability contract does not preserve mandatory abstentions.")
        if contract.get("mas_output_rule") != "context_explanation_and_evidence_trace_only_no_direct_farm_action":
            raise ScenarioIntegrityError(f"{scenario_id} has an unexpected MAS output rule.")

    def _validate_enrichment_rows(self, scenario_id: str, manifest: Mapping[str, str]) -> None:
        for label, row in (
            ("regional calendar", self._regional_calendar[scenario_id]),
            ("management policy", self._management_policy[scenario_id]),
        ):
            self._validate_scoped_identity(scenario_id, manifest, row, label, IDENTITY_FIELDS)
        for label, row in (
            ("district KVK advisory status", self._district_kvk_status[scenario_id]),
            ("natural signal divergence", self._natural_divergence.get(scenario_id)),
        ):
            if row is not None:
                self._validate_scoped_identity(
                    scenario_id, manifest, row, label, ("crop", "state", "district", "decision_date")
                )
        if self._water_status[scenario_id].get("water_context_status") != "available_retrospective_context_only":
            raise ScenarioIntegrityError(f"{scenario_id} has an unexpected water-context status.")
        if self._market_status[scenario_id].get("market_actionability") != "context_only_not_a_market_sale_instruction":
            raise ScenarioIntegrityError(f"{scenario_id} market context exceeds its permitted use.")
        market_source = self._market_context_manifest[scenario_id]
        self._validate_scoped_identity(
            scenario_id,
            manifest,
            market_source,
            "market context source manifest",
            ("crop", "state", "district", "decision_date"),
        )
        if (
            market_source.get("source_url") != manifest.get("market_source_url")
            or market_source.get("raw_path") != manifest.get("market_raw_path")
            or market_source.get("verified_payload_sha256") != manifest.get("market_current_payload_sha256")
            or market_source.get("frozen_payload_sha256") != manifest.get("market_current_payload_sha256")
            or market_source.get("source_status") not in {
                "complete_frozen_official_report_context",
                "no_comparator_in_frozen_official_report",
            }
        ):
            raise ScenarioIntegrityError(f"{scenario_id} market context source manifest disagrees with frozen evidence.")
        if not self._ndvi_timeseries_status[scenario_id].get("satellite_actionability", "").startswith("context_only"):
            raise ScenarioIntegrityError(f"{scenario_id} NDVI timeseries exceeds its permitted use.")
        satellite_source = self._satellite_context_manifest[scenario_id]
        self._validate_scoped_identity(
            scenario_id,
            manifest,
            satellite_source,
            "satellite context source manifest",
            ("crop", "state", "district", "decision_date"),
        )
        for field in ("satellite_item_id", "satellite_datetime_utc"):
            if satellite_source.get(field) != manifest.get(field):
                raise ScenarioIntegrityError(
                    f"{scenario_id} satellite context source manifest differs from the frozen {field}."
                )
        if (
            satellite_source.get("source_id") != "SENTINEL2_L2A_PLANETARY_COMPUTER"
            or not satellite_source.get("item_request_url", "").startswith(
                "https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a/items/"
            )
        ):
            raise ScenarioIntegrityError(f"{scenario_id} satellite context source manifest is incomplete or untrusted.")
        source_status = satellite_source.get("source_status", "")
        response_hash = satellite_source.get("response_sha256", "")
        if source_status == "exact_frozen_item_and_metadata_quality_verified":
            if not SHA256_RE.fullmatch(response_hash):
                raise ScenarioIntegrityError(f"{scenario_id} satellite context source manifest lacks a verified payload hash.")
        elif source_status == "sentinel_ndvi_context_failed":
            if response_hash != "NONE" or not satellite_source.get("error", ""):
                raise ScenarioIntegrityError(f"{scenario_id} satellite no-data source manifest is malformed.")
        else:
            raise ScenarioIntegrityError(f"{scenario_id} has an unknown satellite context source status.")

    def _validate_rag_rows(self, scenario_id: str, manifest: Mapping[str, str]) -> None:
        rows = self._rag_scope[scenario_id]
        source_ids = {row.get("source_document_id", "") for row in rows}
        if source_ids != set(self._rag_documents) or len(rows) != len(source_ids):
            raise ScenarioIntegrityError(f"{scenario_id} does not have one RAG scope row per admitted source.")
        for row in rows:
            self._validate_scoped_identity(
                scenario_id, manifest, row, "RAG scope", ("crop", "state", "district", "decision_date")
            )
            document = self._rag_documents[row["source_document_id"]]
            if not SHA256_RE.fullmatch(document.get("source_raw_sha256", "")):
                raise ScenarioIntegrityError(f"{scenario_id} RAG document has invalid source hash.")
            if not row.get("rag_scope_status") or not row.get("restriction_reason"):
                raise ScenarioIntegrityError(f"{scenario_id} RAG scope is missing its decision or restriction.")

    def _validate_action_rows(self, scenario_id: str, manifest: Mapping[str, str]) -> None:
        rows = self._action_bindings[scenario_id]
        action_ids = {row.get("action_id", "") for row in rows}
        if action_ids != set(self._actions) or len(rows) != len(action_ids):
            raise ScenarioIntegrityError(f"{scenario_id} does not have one binding per official action.")
        for row in rows:
            self._validate_scoped_identity(scenario_id, manifest, row, "action binding", IDENTITY_FIELDS)
            action = self._actions[row["action_id"]]
            if row.get("source_document_id") != action.get("source_document_id"):
                raise ScenarioIntegrityError(f"{scenario_id} action binding source does not match its action record.")
            if row.get("action_record_sha256") != action.get("action_record_sha256"):
                raise ScenarioIntegrityError(f"{scenario_id} action binding hash does not match its action record.")
            if not row.get("binding_status") or not row.get("binding_reason"):
                raise ScenarioIntegrityError(f"{scenario_id} action binding is missing its status or reason.")
            recovery = self._recovered_operation_sources.get(action["source_document_id"])
            if recovery is not None:
                if action.get("source_raw_sha256") != recovery.get("raw_sha256"):
                    raise ScenarioIntegrityError(f"{scenario_id} recovered action source hash does not match its inventory.")
                for action_field, source_field in (("crop", "crop_scope"), ("state_scope", "state_scope"), ("season_scope", "season_scope")):
                    if action.get(action_field) != recovery.get(source_field):
                        raise ScenarioIntegrityError(
                            f"{scenario_id} recovered action {action_field} does not match source inventory."
                        )

    def _validate_regional_operation_plan_rows(self, scenario_id: str, manifest: Mapping[str, str]) -> None:
        summary = self._regional_operation_plan_summary[scenario_id]
        self._validate_scoped_identity(scenario_id, manifest, summary, "regional operation-plan summary", IDENTITY_FIELDS)
        if _canonical_row_hash(summary, "plan_summary_sha256") != summary.get("plan_summary_sha256"):
            raise ScenarioIntegrityError(f"{scenario_id} regional operation-plan summary hash mismatch.")
        if summary.get("direct_farm_action_status") != "not_issued_no_farm_specific_observation_or_treatment_trigger":
            raise ScenarioIntegrityError(f"{scenario_id} regional operation-plan summary exceeds the action boundary.")
        items = self._regional_operation_plan_items[scenario_id]
        if len({item.get("plan_item_id", "") for item in items}) != len(items):
            raise ScenarioIntegrityError(f"{scenario_id} has duplicate regional operation-plan items.")
        expected_conditional = {
            row["action_id"]
            for row in self._action_bindings[scenario_id]
            if row.get("binding_status") == "conditionally_applicable_pending_unobserved_farm_condition"
        }
        actual_conditional: set[str] = set()
        reference_count = 0
        bindings_by_action = {row["action_id"]: row for row in self._action_bindings[scenario_id]}
        for item in items:
            self._validate_scoped_identity(scenario_id, manifest, item, "regional operation-plan item", IDENTITY_FIELDS)
            if _canonical_row_hash(item, "plan_item_sha256") != item.get("plan_item_sha256"):
                raise ScenarioIntegrityError(f"{scenario_id} regional operation-plan item hash mismatch.")
            if item.get("plan_item_type") == "time_valid_source_quoted_conditional_operation":
                action_id = item.get("action_id", "")
                action, binding = self._actions.get(action_id), bindings_by_action.get(action_id)
                if action is None or binding is None:
                    raise ScenarioIntegrityError(f"{scenario_id} regional operation-plan item references an unknown action.")
                if binding.get("binding_status") != "conditionally_applicable_pending_unobserved_farm_condition":
                    raise ScenarioIntegrityError(f"{scenario_id} regional operation-plan item does not retain a conditional binding.")
                if (
                    item.get("source_document_id") != action.get("source_document_id")
                    or item.get("action_record_sha256") != action.get("action_record_sha256")
                    or item.get("source_binding_status") != binding.get("binding_status")
                    or item.get("missing_evidence") != binding.get("binding_reason")
                ):
                    raise ScenarioIntegrityError(f"{scenario_id} regional operation-plan operation provenance mismatch.")
                actual_conditional.add(action_id)
            else:
                reference_count += 1
                if item.get("action_id") or item.get("action_record_sha256"):
                    raise ScenarioIntegrityError(f"{scenario_id} regional reference item unexpectedly contains an action.")
        if actual_conditional != expected_conditional:
            raise ScenarioIntegrityError(f"{scenario_id} regional operation-plan conditional actions differ from bindings.")
        if int(summary.get("conditional_source_quoted_operation_count", "-1")) != len(actual_conditional):
            raise ScenarioIntegrityError(f"{scenario_id} regional operation-plan conditional count mismatch.")
        if summary.get("conditional_action_ids", "") != ";".join(sorted(actual_conditional)):
            raise ScenarioIntegrityError(f"{scenario_id} regional operation-plan conditional action IDs mismatch.")
        if int(summary.get("regional_reference_item_count", "-1")) != reference_count or int(summary.get("total_plan_item_count", "-1")) != len(items):
            raise ScenarioIntegrityError(f"{scenario_id} regional operation-plan item counts mismatch.")

    def _validate_postharvest_global_rows(self, benchmark_states: set[str]) -> None:
        """Validate the fourth enrichment before any agent can consume it.

        This is deliberately separate from the regional-operation-plan validator:
        postharvest sources have different temporal semantics.  Crop technical
        passages are conditional references, while facility/warehouse/route
        records are collection-date infrastructure context only.
        """
        benchmark_crops = {row["crop"] for row in self._manifest.values()}
        if len(self._postharvest_source_inventory) != 16:
            raise ScenarioIntegrityError("Postharvest source inventory has an unexpected source count.")
        for source_id, source in self._postharvest_source_inventory.items():
            relative, expected = source.get("raw_path", ""), source.get("raw_sha256", "")
            if not relative or not SHA256_RE.fullmatch(expected):
                raise ScenarioIntegrityError(f"Postharvest source {source_id} has incomplete raw provenance.")
            path = (self.enriched_root / relative).resolve()
            if self.enriched_root not in path.parents or not path.is_file():
                raise ScenarioIntegrityError(f"Postharvest source {source_id} raw artifact is missing or outside enrichment storage.")
            if _payload_hash(path, False) != expected:
                raise ScenarioIntegrityError(f"Postharvest source {source_id} raw artifact hash mismatch.")
        profile_crops = {row.get("crop", "") for row in self._postharvest_handling_profiles.values()}
        if profile_crops != benchmark_crops or len(self._postharvest_handling_profiles) != len(benchmark_crops):
            raise ScenarioIntegrityError("Postharvest handling profiles do not cover exactly the benchmark crops.")
        for profile_id, profile in self._postharvest_handling_profiles.items():
            if _canonical_row_hash(profile, "profile_sha256") != profile.get("profile_sha256"):
                raise ScenarioIntegrityError(f"Postharvest handling profile hash mismatch: {profile_id}.")
            if profile.get("farmer_output_status") != "conditional_plan_items_available_no_direct_farm_action":
                raise ScenarioIntegrityError(f"Postharvest profile {profile_id} exceeds the direct-action boundary.")
        for operation_id, operation in self._postharvest_operation_library.items():
            if operation.get("profile_id") not in self._postharvest_handling_profiles:
                raise ScenarioIntegrityError(f"Postharvest operation {operation_id} references an unknown profile.")
            if operation.get("crop") != self._postharvest_handling_profiles[operation["profile_id"]].get("crop"):
                raise ScenarioIntegrityError(f"Postharvest operation {operation_id} crop differs from its profile.")
            source = self._postharvest_source_inventory.get(operation.get("source_document_id", ""))
            if source is None or operation.get("source_raw_sha256") != source.get("raw_sha256"):
                raise ScenarioIntegrityError(f"Postharvest operation {operation_id} source provenance mismatch.")
            if _canonical_row_hash(operation, "operation_sha256") != operation.get("operation_sha256"):
                raise ScenarioIntegrityError(f"Postharvest operation hash mismatch: {operation_id}.")
            if (
                operation.get("actionability_status")
                != "conditional_postharvest_planning_reference_not_direct_farm_action"
                or not operation.get("conditions_text")
                or not operation.get("missing_observation")
            ):
                raise ScenarioIntegrityError(f"Postharvest operation {operation_id} lacks its conditional safety boundary.")
        for passage_id, passage in self._postharvest_rag_passages.items():
            source = self._postharvest_source_inventory.get(passage.get("source_document_id", ""))
            if source is None or passage.get("source_raw_sha256") != source.get("raw_sha256"):
                raise ScenarioIntegrityError(f"Postharvest RAG passage {passage_id} source provenance mismatch.")
            if passage.get("crop") not in benchmark_crops or _canonical_row_hash(passage, "passage_sha256") != passage.get("passage_sha256"):
                raise ScenarioIntegrityError(f"Postharvest RAG passage hash/scope is invalid: {passage_id}.")
            if "conditional" not in passage.get("allowed_use", "").lower():
                raise ScenarioIntegrityError(f"Postharvest RAG passage {passage_id} is not conditional-only.")
        for label, rows, identifier, digest_field in (
            ("NHB facility", self._postharvest_nhb_facilities, "facility_id", "facility_sha256"),
            ("WDRA warehouse", self._postharvest_wdra_warehouses, "warehouse_id", "warehouse_sha256"),
        ):
            for record_id, row in rows.items():
                source = self._postharvest_source_inventory.get(row.get("source_document_id", ""))
                if source is None or row.get("source_raw_sha256") != source.get("raw_sha256"):
                    raise ScenarioIntegrityError(f"{label} {record_id} source provenance mismatch.")
                if _canonical_row_hash(row, digest_field) != row.get(digest_field):
                    raise ScenarioIntegrityError(f"{label} {record_id} hash mismatch.")
        for state, rows in self._postharvest_state_infrastructure.items():
            if state not in benchmark_states:
                raise ScenarioIntegrityError(f"Postharvest state infrastructure includes unscoped state: {state}.")
            for row in rows:
                source = self._postharvest_source_inventory.get(row.get("source_document_id", ""))
                if source is None or row.get("source_raw_sha256") != source.get("raw_sha256"):
                    raise ScenarioIntegrityError(f"Postharvest state infrastructure source mismatch for {state}.")
                if _canonical_row_hash(row, "infrastructure_sha256") != row.get("infrastructure_sha256"):
                    raise ScenarioIntegrityError(f"Postharvest state infrastructure hash mismatch for {state}.")
        expected_provenance_roles = {
            "source_inventory", "nhb_facility_records", "nhb_state_components", "osrm_static_routes",
            "wdra_registry_madhya_pradesh", "wdra_registry_maharashtra", "wdra_registry_punjab",
            "wdra_registry_rajasthan", "wdra_registry_tamil_nadu", "frozen_scenario_manifest",
        }
        provenance = {row.get("artifact_role", ""): row for row in self._postharvest_logistics_provenance}
        if set(provenance) != expected_provenance_roles or len(provenance) != len(self._postharvest_logistics_provenance):
            raise ScenarioIntegrityError("Postharvest logistics provenance is incomplete or duplicated.")
        for role, row in provenance.items():
            relative, expected = row.get("input_path", ""), row.get("input_sha256", "")
            root = self.project_root if relative.startswith("data/") else self.enriched_root
            path = (root / relative).resolve()
            if root not in path.parents or not path.is_file() or not SHA256_RE.fullmatch(expected):
                raise ScenarioIntegrityError(f"Postharvest logistics provenance path is invalid for {role}.")
            if _payload_hash(path, False) != expected:
                raise ScenarioIntegrityError(f"Postharvest logistics provenance hash mismatch for {role}.")

    def _validate_postharvest_rows(self, scenario_id: str, manifest: Mapping[str, str]) -> None:
        context = self._postharvest_logistics_context[scenario_id]
        self._validate_scoped_identity(scenario_id, manifest, context, "postharvest logistics context", IDENTITY_FIELDS)
        if _canonical_row_hash(context, "context_sha256") != context.get("context_sha256"):
            raise ScenarioIntegrityError(f"{scenario_id} postharvest logistics context hash mismatch.")
        if context.get("context_status") != "available_source_linked_postharvest_context":
            raise ScenarioIntegrityError(f"{scenario_id} postharvest logistics context has an unexpected status.")
        profile = self._postharvest_handling_profiles.get(context.get("profile_id", ""))
        if profile is None or profile.get("crop") != manifest.get("crop"):
            raise ScenarioIntegrityError(f"{scenario_id} postharvest profile does not match the scenario crop.")
        items = self._postharvest_plan_items[scenario_id]
        expected_operation_ids = {
            operation_id
            for operation_id, operation in self._postharvest_operation_library.items()
            if operation.get("crop") == manifest.get("crop")
        }
        actual_operation_ids: set[str] = set()
        for item in items:
            self._validate_scoped_identity(scenario_id, manifest, item, "postharvest plan item", IDENTITY_FIELDS)
            if _canonical_row_hash(item, "plan_item_sha256") != item.get("plan_item_sha256"):
                raise ScenarioIntegrityError(f"{scenario_id} postharvest plan item hash mismatch.")
            operation = self._postharvest_operation_library.get(item.get("operation_id", ""))
            if operation is None or item.get("profile_id") != context.get("profile_id"):
                raise ScenarioIntegrityError(f"{scenario_id} postharvest plan item has an unknown operation/profile.")
            for field in (
                "crop", "operation_text", "method_or_parameter", "conditions_text", "missing_observation",
                "actionability_status", "source_document_id", "source_title", "source_url", "source_raw_sha256",
                "source_location", "source_quote", "temporal_interpretation",
            ):
                if item.get(field) != operation.get(field):
                    raise ScenarioIntegrityError(f"{scenario_id} postharvest plan item differs from operation field {field}.")
            if (
                item.get("item_status") != "conditional_postharvest_operation_pending_lot_observation"
                or item.get("actionability_status") != "conditional_postharvest_planning_reference_not_direct_farm_action"
            ):
                raise ScenarioIntegrityError(f"{scenario_id} postharvest plan item exceeds the action boundary.")
            actual_operation_ids.add(item["operation_id"])
        if actual_operation_ids != expected_operation_ids or len(actual_operation_ids) != len(items):
            raise ScenarioIntegrityError(f"{scenario_id} postharvest plan items differ from its crop profile.")
        if int(context.get("postharvest_plan_item_count", "-1")) != len(items):
            raise ScenarioIntegrityError(f"{scenario_id} postharvest plan-item count mismatch.")
        scope = self._postharvest_rag_scope[scenario_id]
        expected_passage_ids = {f"POSTHARVEST_PASSAGE__{operation_id}" for operation_id in expected_operation_ids}
        actual_passage_ids = {row.get("passage_id", "") for row in scope}
        if actual_passage_ids != expected_passage_ids or len(actual_passage_ids) != len(scope):
            raise ScenarioIntegrityError(f"{scenario_id} postharvest RAG scope differs from its crop plan.")
        for row in scope:
            if _canonical_row_hash(row, "scope_sha256") != row.get("scope_sha256"):
                raise ScenarioIntegrityError(f"{scenario_id} postharvest RAG scope hash mismatch.")
            passage = self._postharvest_rag_passages.get(row.get("passage_id", ""))
            if passage is None or passage.get("crop") != manifest.get("crop"):
                raise ScenarioIntegrityError(f"{scenario_id} postharvest RAG scope crosses crop boundaries.")
            if row.get("crop_scope_status") != "pass_exact_crop":
                raise ScenarioIntegrityError(f"{scenario_id} postharvest RAG scope is not exact-crop admitted.")
        summary = self._postharvest_site_summary[manifest["site_id"]]
        if any(summary.get(field) != manifest.get(field) for field in ("crop", "state", "district")):
            raise ScenarioIntegrityError(f"{scenario_id} postharvest site summary identity mismatch.")
        if _canonical_row_hash(summary, "site_summary_sha256") != summary.get("site_summary_sha256"):
            raise ScenarioIntegrityError(f"{scenario_id} postharvest site summary hash mismatch.")
        site_contexts = self._postharvest_site_facility_context[manifest["site_id"]]
        facility_count = warehouse_count = 0
        for row in site_contexts:
            if any(row.get(field) != manifest.get(field) for field in ("site_id", "crop", "state", "district")):
                raise ScenarioIntegrityError(f"{scenario_id} postharvest facility context identity mismatch.")
            if _canonical_row_hash(row, "site_context_sha256") != row.get("site_context_sha256"):
                raise ScenarioIntegrityError(f"{scenario_id} postharvest facility context hash mismatch.")
            if row.get("context_kind") == "nhb_mapped_project_proximity":
                candidate = self._postharvest_nhb_facilities.get(row.get("candidate_id", ""))
                facility_count += 1
            elif row.get("context_kind") == "wdra_registered_warehouse_district_match":
                candidate = self._postharvest_wdra_warehouses.get(row.get("candidate_id", ""))
                warehouse_count += 1
            else:
                raise ScenarioIntegrityError(f"{scenario_id} has an unsupported postharvest facility context kind.")
            if candidate is None or row.get("source_document_id") != candidate.get("source_document_id"):
                raise ScenarioIntegrityError(f"{scenario_id} postharvest facility context candidate mismatch.")
        if (
            int(summary.get("facility_candidate_count", "-1")) != facility_count
            or int(summary.get("warehouse_candidate_count", "-1")) != warehouse_count
            or int(context.get("facility_candidate_count", "-1")) != facility_count
            or int(context.get("warehouse_candidate_count", "-1")) != warehouse_count
        ):
            raise ScenarioIntegrityError(f"{scenario_id} postharvest facility counts mismatch.")
        routes = self._postharvest_static_route_context.get(manifest["site_id"], [])
        for row in routes:
            if any(row.get(field) != manifest.get(field) for field in ("site_id", "crop", "state", "district")):
                raise ScenarioIntegrityError(f"{scenario_id} postharvest route identity mismatch.")
            if row.get("candidate_id") not in self._postharvest_nhb_facilities:
                raise ScenarioIntegrityError(f"{scenario_id} postharvest route references an unknown NHB facility.")
            raw_path = (self.enriched_root / row.get("raw_path", "")).resolve()
            if self.enriched_root not in raw_path.parents or not raw_path.is_file():
                raise ScenarioIntegrityError(f"{scenario_id} postharvest route raw artifact is missing.")
            if _payload_hash(raw_path, False) != row.get("raw_sha256", ""):
                raise ScenarioIntegrityError(f"{scenario_id} postharvest route raw artifact hash mismatch.")
            if _canonical_row_hash(row, "route_sha256") != row.get("route_sha256"):
                raise ScenarioIntegrityError(f"{scenario_id} postharvest route hash mismatch.")
        if (
            int(summary.get("static_road_route_count", "-1")) != len(routes)
            or int(context.get("static_road_route_count", "-1")) != len(routes)
        ):
            raise ScenarioIntegrityError(f"{scenario_id} postharvest static-route count mismatch.")

    def _verify_postharvest_sources(self, source_ids: Sequence[str]) -> None:
        """Reverify scenario-relevant postharvest source snapshots once per loader."""
        for source_id in source_ids:
            if source_id in self._verified_postharvest_sources:
                continue
            source = self._postharvest_source_inventory.get(source_id)
            if source is None:
                raise ScenarioIntegrityError(f"Unknown postharvest source: {source_id}.")
            path = (self.enriched_root / source["raw_path"]).resolve()
            if self.enriched_root not in path.parents or not path.is_file():
                raise ScenarioIntegrityError(f"Postharvest source artifact is missing: {source_id}.")
            if _payload_hash(path, False) != source["raw_sha256"]:
                raise ScenarioIntegrityError(f"Postharvest source artifact hash mismatch: {source_id}.")
            self._verified_postharvest_sources.add(source_id)

    def _verify_recovered_operation_sources(self, source_ids: Sequence[str]) -> None:
        """Verify only source artifacts relevant to this scenario, once per loader."""
        for source_id in source_ids:
            if source_id in self._verified_recovered_operation_sources:
                continue
            source = self._recovered_operation_sources[source_id]
            for path_field, hash_field in (
                ("raw_path", "raw_sha256"),
                ("extracted_text_path", "extracted_text_sha256"),
                ("http_metadata_path", "http_metadata_sha256"),
                ("publication_page_raw_path", "publication_page_raw_sha256"),
                ("scope_page_image_path", "scope_page_image_sha256"),
                ("operation_page_image_path", "operation_page_image_sha256"),
            ):
                relative, expected = source.get(path_field, ""), source.get(hash_field, "")
                if not relative and not expected:
                    continue
                if not relative or not SHA256_RE.fullmatch(expected):
                    raise ScenarioIntegrityError(f"Recovered source {source_id} has incomplete {path_field} provenance.")
                path = (self.enriched_root / relative).resolve()
                if self.enriched_root not in path.parents or not path.is_file():
                    raise ScenarioIntegrityError(f"Recovered source {source_id} artifact is missing or outside enrichment storage.")
                if _payload_hash(path, False) != expected:
                    raise ScenarioIntegrityError(f"Recovered source {source_id} artifact hash mismatch for {path_field}.")
            self._verified_recovered_operation_sources.add(source_id)

    @staticmethod
    def _validate_scoped_identity(
        scenario_id: str,
        manifest: Mapping[str, str],
        row: Mapping[str, str],
        label: str,
        fields: Sequence[str],
    ) -> None:
        for field in fields:
            if row.get(field) != manifest.get(field):
                raise ScenarioIntegrityError(f"{scenario_id} {label} has mismatched {field}.")

    def _verify_scenario_payloads(self, manifest: Mapping[str, str]) -> None:
        checks = (
            ("weather_raw_path", "weather_current_response_sha256", False, True),
            ("market_raw_path", "market_current_payload_sha256", True, True),
            ("satellite_raw_path", "satellite_response_sha256", False, False),
        )
        for path_field, hash_field, canonical_json, required in checks:
            relative = manifest.get(path_field, "")
            expected = manifest.get(hash_field, "")
            if not relative:
                if required:
                    raise ScenarioIntegrityError(f"{manifest['scenario_id']} lacks required {path_field}.")
                continue
            if not SHA256_RE.fullmatch(expected):
                raise ScenarioIntegrityError(f"{manifest['scenario_id']} has invalid {hash_field}.")
            raw_path = (self.scenario_root / relative).resolve()
            if self.scenario_root not in raw_path.parents or not raw_path.is_file():
                raise ScenarioIntegrityError(f"{manifest['scenario_id']} raw payload is missing or outside the scenario root.")
            if _payload_hash(raw_path, canonical_json) != expected:
                raise ScenarioIntegrityError(f"{manifest['scenario_id']} raw payload hash mismatch for {path_field}.")
        if not manifest.get("satellite_raw_path"):
            registry_scene = self._preflight_sentinel[manifest["site_id"]]
            if manifest.get("satellite_item_id") != registry_scene.get("selected_item_id"):
                raise ScenarioIntegrityError(f"{manifest['scenario_id']} anchor Sentinel item differs from registry evidence.")

    def _verify_satellite_context_payload(self, source_manifest: Mapping[str, str]) -> None:
        """Verify the exact Sentinel item payload used by the context agent once."""
        scenario_id = source_manifest["scenario_id"]
        if scenario_id in self._verified_satellite_context_payloads:
            return
        relative, expected = source_manifest.get("raw_path", ""), source_manifest.get("response_sha256", "")
        if source_manifest.get("source_status") == "sentinel_ndvi_context_failed":
            # The source record still preserves the exact STAC item URL, but
            # no item response was saved after point sampling failed.
            return
        if not relative or not SHA256_RE.fullmatch(expected):
            raise ScenarioIntegrityError(f"{scenario_id} satellite context source has incomplete raw provenance.")
        path = (self.enriched_root / relative).resolve()
        if self.enriched_root not in path.parents or not path.is_file():
            raise ScenarioIntegrityError(f"{scenario_id} satellite context raw payload is missing or outside enrichment storage.")
        if _payload_hash(path, False) != expected:
            raise ScenarioIntegrityError(f"{scenario_id} satellite context raw payload hash mismatch.")
        self._verified_satellite_context_payloads.add(scenario_id)
