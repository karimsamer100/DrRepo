from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ReadinessEvidence:
    path: str
    reason: str
    detail: str | None = None


@dataclass
class ReadinessFinding:
    id: str
    title: str
    description: str
    category: str
    severity: str
    confidence: str
    evidence: list[ReadinessEvidence] = field(default_factory=list)
    affected_files: list[str] = field(default_factory=list)
    why_it_matters: str = ""
    suggested_fix: str = ""
    success_check: str = ""


@dataclass
class DimensionAssessment:
    id: str
    title: str
    applicability: str
    score: int | None
    status: str
    confidence: str
    summary: str
    strengths: list[str] = field(default_factory=list)
    findings: list[ReadinessFinding] = field(default_factory=list)
    blockers: list[ReadinessFinding] = field(default_factory=list)
    evidence: list[ReadinessEvidence] = field(default_factory=list)
    unverified_checks: list[str] = field(default_factory=list)


@dataclass
class DevOpsReadinessAssessment:
    applicability: str
    verdict: str
    observed_score: int | None
    evidence_confidence: str
    dimensions: list[DimensionAssessment]
    strengths: list[str]
    blockers: list[ReadinessFinding]
    risks: list[ReadinessFinding]
    evidence_gaps: list[str]
    next_best_step: str
    recommendations: list[dict[str, Any]]


def to_plain_dict(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, list):
        return [to_plain_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: to_plain_dict(item) for key, item in value.items()}
    return value
