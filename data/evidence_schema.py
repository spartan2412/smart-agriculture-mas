"""Typed, provenance-carrying evidence contracts for the benchmark MAS path.

The legacy ``AgentEvidence`` dataclass remains unchanged for the pilot system.
These models are deliberately separate until the provenance-constrained graph
is implemented.  Future benchmark agents must emit ``TypedEvidenceClaim``
instances rather than unscoped recommendation strings.
"""
from __future__ import annotations

from hashlib import sha256
import json
from enum import Enum
from typing import Any, Dict, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DecisionDomain(str, Enum):
    """Domains whose claims can be compared by a future conflict resolver."""

    WEATHER_CONTEXT = "weather_context"
    SOIL_CONTEXT = "soil_context"
    SATELLITE_CONTEXT = "satellite_context"
    MARKET_CONTEXT = "market_context"
    REGIONAL_CALENDAR = "regional_calendar"
    FERTILIZER_BASELINE = "fertilizer_baseline"
    CROP_PROTECTION_SAFETY = "crop_protection_safety"
    OFFICIAL_OPERATION = "official_operation"
    POSTHARVEST_LOGISTICS = "postharvest_logistics"
    REGULATORY_CONTEXT = "regulatory_context"
    SYSTEM_SAFETY = "system_safety"


class ClaimDisposition(str, Enum):
    """Whether evidence is usable, conditional, blocked, or unavailable."""

    CONTEXT = "context"
    SUPPORTED_OPERATION = "supported_operation"
    CONDITIONAL_OPERATION = "conditional_operation"
    BLOCKED = "blocked"
    ABSTAIN = "abstain"
    NO_DATA = "no_data"


class AllowedUse(str, Enum):
    """Maximum scope that an agent may assign to a source-backed claim."""

    CONTEXT_ONLY = "context_only"
    REGIONAL_POLICY_ONLY = "regional_policy_only"
    CONDITIONAL_OPERATION_ONLY = "conditional_operation_only"
    REGULATORY_LOOKUP_ONLY = "regulatory_lookup_only"
    UNAVAILABLE = "unavailable"


class GateResult(str, Enum):
    PASS = "pass"
    BLOCKED = "blocked"
    ABSTAIN = "abstain"
    NOT_APPLICABLE = "not_applicable"


class SourceCitation(BaseModel):
    """Immutable source facts carried with one typed claim."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_document_id: Optional[str] = None
    official_url: Optional[str] = None
    raw_path: Optional[str] = None
    raw_sha256: Optional[str] = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    locator: Optional[str] = None
    source_role: Optional[str] = None


def _canonical_json_value(value: Any) -> Any:
    """Normalize nested metadata before hashing it into a stable claim ID."""
    if isinstance(value, BaseModel):
        return _canonical_json_value(value.model_dump(mode="json"))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_json_value(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_json_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        normalized = [_canonical_json_value(item) for item in value]
        return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True, default=str))
    return value


def stable_claim_id(values: Mapping[str, Any]) -> str:
    """Return a deterministic identity for one immutable evidence claim.

    The identifier deliberately covers the source, scope, gate and claim
    content that the coordinator is allowed to compare.  Presentation-only
    bounded-LLM metadata is excluded: an LLM selection can never create a new
    evidence claim or change its provenance identity.
    """
    source = _canonical_json_value(values.get("source", {}))
    metadata = dict(values.get("metadata") or {})
    metadata.pop("bounded_llm", None)
    payload = {
        "scenario_id": values.get("scenario_id", ""),
        "agent_name": values.get("agent_name", ""),
        "decision_domain": getattr(values.get("decision_domain"), "value", values.get("decision_domain", "")),
        "disposition": getattr(values.get("disposition"), "value", values.get("disposition", "")),
        "allowed_use": getattr(values.get("allowed_use"), "value", values.get("allowed_use", "")),
        "claim": values.get("claim", ""),
        "summary": values.get("summary", ""),
        "reasoning": values.get("reasoning", ""),
        "confidence": values.get("confidence", ""),
        "source": source,
        "spatial_scope": values.get("spatial_scope", ""),
        "temporal_scope": values.get("temporal_scope", ""),
        "quality": values.get("quality", ""),
        "gate_result": getattr(values.get("gate_result"), "value", values.get("gate_result", "")),
        "block_reason": values.get("block_reason", ""),
        "metadata": _canonical_json_value(metadata),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(canonical.encode("utf-8")).hexdigest()


class TypedEvidenceClaim(BaseModel):
    """Single claim emitted by a benchmark MAS component.

    A blocked/abstained claim must name its reason.  This prevents a later
    coordinator from turning unavailable field evidence into a recommendation.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")
    scenario_id: str = Field(min_length=1)
    agent_name: str = Field(min_length=1)
    decision_domain: DecisionDomain
    disposition: ClaimDisposition
    allowed_use: AllowedUse
    claim: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    reasoning: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    source: SourceCitation
    spatial_scope: str = Field(min_length=1)
    temporal_scope: str = Field(min_length=1)
    quality: str = Field(min_length=1)
    gate_result: GateResult
    block_reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _assign_stable_claim_id(cls, value: Any) -> Any:
        """Derive claim identities inside the immutable contract, not agents."""
        if isinstance(value, cls) or not isinstance(value, Mapping):
            return value
        values = dict(value)
        # Always derive the identifier from the immutable evidence payload so
        # callers cannot attach a stale or arbitrary claim ID.
        values["claim_id"] = stable_claim_id(values)
        return values

    def model_copy(
        self,
        *,
        update: Optional[Dict[str, Any]] = None,
        deep: bool = False,
    ) -> "TypedEvidenceClaim":
        """Revalidate copies so a changed evidence field receives a new ID.

        Pydantic's default ``model_copy`` intentionally skips validation.  The
        benchmark uses it only to append presentation-only bounded-LLM
        metadata, but this override also closes the stale-ID path for any
        future caller that attempts to alter a claim's evidence fields.
        """
        copied = super().model_copy(update=update, deep=deep)
        if not update:
            return copied
        return type(self).model_validate(copied.model_dump(mode="python"))

    @model_validator(mode="after")
    def _require_safe_block_reason(self) -> "TypedEvidenceClaim":
        if self.disposition in {
            ClaimDisposition.BLOCKED,
            ClaimDisposition.ABSTAIN,
            ClaimDisposition.NO_DATA,
        } and not self.block_reason:
            raise ValueError("blocked, abstained, and no-data claims require a block_reason")
        if self.allowed_use == AllowedUse.UNAVAILABLE and self.disposition not in {
            ClaimDisposition.BLOCKED,
            ClaimDisposition.ABSTAIN,
            ClaimDisposition.NO_DATA,
        }:
            raise ValueError("unavailable evidence cannot produce a usable claim")
        return self
