from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ArchitectureEvidence:
    path: str
    reason: str
    detail: str | None = None


@dataclass
class ArchitectureNode:
    id: str
    label: str
    kind: str
    path: str
    language: str
    layer: str
    symbols: list[str] = field(default_factory=list)
    confidence: str = "medium"
    evidence: list[ArchitectureEvidence] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    risk: dict[str, Any] = field(default_factory=dict)


@dataclass
class ArchitectureEdge:
    source: str
    target: str
    kind: str
    confidence: str
    evidence: list[ArchitectureEvidence] = field(default_factory=list)


@dataclass
class ArchitectureLayer:
    id: str
    label: str
    node_ids: list[str]
    confidence: str
    evidence: list[ArchitectureEvidence] = field(default_factory=list)


@dataclass
class ArchitectureCycle:
    id: str
    node_ids: list[str]
    paths: list[str]
    classification: str
    confidence: str
    evidence: list[ArchitectureEvidence] = field(default_factory=list)


@dataclass
class RiskFactor:
    id: str
    label: str
    contribution: int
    evidence: list[str] = field(default_factory=list)


@dataclass
class RiskHotspot:
    id: str
    rank: int
    node_id: str
    path: str
    title: str
    risk_score: int
    risk_level: str
    confidence: str
    factors: list[RiskFactor]
    findings: list[dict[str, Any]] = field(default_factory=list)
    test_status: str = "unknown"
    why_it_matters: str = ""
    recommended_action: str = ""
    success_check: str = ""


@dataclass
class ArchitectureAssessment:
    status: str
    confidence: str
    summary: str
    nodes: list[ArchitectureNode]
    edges: list[ArchitectureEdge]
    layers: list[ArchitectureLayer]
    entry_points: list[dict[str, Any]]
    external_integrations: list[dict[str, Any]]
    cycles: list[ArchitectureCycle]
    hotspots: list[RiskHotspot]
    evidence_gaps: list[str]
    limitations: list[str]


def to_plain_dict(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, list):
        return [to_plain_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: to_plain_dict(item) for key, item in value.items()}
    return value
