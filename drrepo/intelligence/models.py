from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EvidenceItem:
    path: str
    reason: str
    detail: str | None = None


@dataclass
class ProjectIdentity:
    primary_language: str
    project_type: str
    secondary_project_types: list[str]
    architecture_type: str | None
    domain_specializations: list[str]
    frameworks: list[str]
    interfaces: list[str]
    package_layout: str
    confidence: str
    evidence: list[EvidenceItem] = field(default_factory=list)


@dataclass
class EntryPoint:
    kind: str
    path: str
    symbol: str | None = None
    command: str | None = None
    confidence: str = "medium"
    evidence: list[EvidenceItem] = field(default_factory=list)


@dataclass
class Runnability:
    install_commands: list[str]
    run_commands: list[str]
    test_commands: list[str]
    build_commands: list[str]
    status: str
    confidence: str
    missing_requirements: list[str]
    evidence: list[EvidenceItem] = field(default_factory=list)


@dataclass
class ArchitectureSummary:
    backend_present: bool
    frontend_present: bool
    cli_present: bool
    api_present: bool
    ml_present: bool
    notebooks_present: bool
    database_signals: list[str]
    container_signals: list[str]
    ci_signals: list[str]
    important_directories: list[str]


@dataclass
class ProjectUnderstanding:
    project_identity: ProjectIdentity
    entry_points: list[EntryPoint]
    runnability: Runnability
    architecture_summary: ArchitectureSummary


@dataclass
class ExecutiveReport:
    headline: str
    one_sentence_summary: str
    project_description: str
    verdict: str
    observed_score: int | None
    evidence_confidence: str
    strongest_signals: list[str]
    primary_risks: list[str]
    biggest_gap: str
    next_best_step: str
    evidence_gaps: list[str]
    user_profile_context: str


@dataclass
class StructuredRecommendation:
    id: str
    title: str
    category: str
    priority: int
    severity: str
    confidence: str
    impact: str
    effort: str
    recommendation_type: str
    why_it_matters: str
    evidence: list[str]
    related_findings: list[str]
    recommended_steps: list[str]
    optional_example: str | None
    success_check: str


def to_plain_dict(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, list):
        return [to_plain_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: to_plain_dict(item) for key, item in value.items()}
    return value
