from __future__ import annotations

import importlib.metadata
import importlib.util
import sys
import time
from dataclasses import dataclass
from typing import Callable, Iterable, Literal

from .models import ToolResult

SourceType = Literal["local_path", "github_url"]
AnalysisMode = Literal["quick_safe", "deep_local", "deep_isolated"]

SOURCE_TYPES: tuple[SourceType, ...] = ("local_path", "github_url")
ANALYSIS_MODES: tuple[AnalysisMode, ...] = ("quick_safe", "deep_local", "deep_isolated")

REMOTE_SAFETY_POLICY = (
    "Remote GitHub audits never execute target repository tests or coverage on the host. "
    "Use quick_safe for github_url by default; deep_isolated is explicit opt-in and runs supported verification inside Docker."
)


@dataclass(frozen=True)
class AnalyzerDefinition:
    analyzer_id: str
    display_name: str
    section: str
    category: str
    executes_repository_code: bool
    supported_source_types: tuple[SourceType, ...]
    supported_analysis_modes: tuple[AnalysisMode, ...]
    module_name: str | None
    default_timeout_seconds: int
    core: bool


@dataclass(frozen=True)
class AnalyzerCapability:
    analyzer_id: str
    display_name: str
    section: str
    category: str
    executes_repository_code: bool
    supported_source_types: tuple[SourceType, ...]
    supported_analysis_modes: tuple[AnalysisMode, ...]
    available: bool
    installed_version: str | None
    unavailable_reason: str | None
    default_timeout_seconds: int
    core: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "analyzer_id": self.analyzer_id,
            "display_name": self.display_name,
            "section": self.section,
            "category": self.category,
            "executes_repository_code": self.executes_repository_code,
            "supported_source_types": list(self.supported_source_types),
            "supported_analysis_modes": list(self.supported_analysis_modes),
            "available": self.available,
            "installed_version": self.installed_version,
            "unavailable_reason": self.unavailable_reason,
            "default_timeout_seconds": self.default_timeout_seconds,
            "core": self.core,
        }


def _definition(
    analyzer_id: str,
    display_name: str,
    section: str,
    category: str,
    executes_repository_code: bool,
    modes: tuple[AnalysisMode, ...],
    module_name: str | None,
    timeout: int,
    core: bool,
    sources: tuple[SourceType, ...] = SOURCE_TYPES,
) -> AnalyzerDefinition:
    return AnalyzerDefinition(
        analyzer_id=analyzer_id,
        display_name=display_name,
        section=section,
        category=category,
        executes_repository_code=executes_repository_code,
        supported_source_types=sources,
        supported_analysis_modes=modes,
        module_name=module_name,
        default_timeout_seconds=timeout,
        core=core,
    )


ANALYZERS: tuple[AnalyzerDefinition, ...] = (
    _definition("readme", "README analyzer", "repository_analysis", "documentation", False, ANALYSIS_MODES, None, 10, True),
    _definition("structure", "Structure analyzer", "repository_analysis", "structure", False, ANALYSIS_MODES, None, 10, True),
    _definition("ruff", "Ruff", "static_analysis", "code_quality", False, ANALYSIS_MODES, "ruff", 30, False),
    _definition("bandit", "Bandit", "static_analysis", "security", False, ANALYSIS_MODES, "bandit", 30, False),
    _definition("radon", "Radon", "static_analysis", "maintainability", False, ANALYSIS_MODES, "radon", 30, False),
    _definition("pytest", "pytest", "test_analysis", "testing", True, ("deep_local", "deep_isolated"), "pytest", 60, False, SOURCE_TYPES),
    _definition("coverage", "coverage", "test_analysis", "testing", True, ("deep_local", "deep_isolated"), "coverage", 60, False, SOURCE_TYPES),
    _definition("ci_config", "CI configuration", "readiness", "ci_cd", False, ANALYSIS_MODES, None, 10, True),
    _definition("container_config", "Container configuration", "readiness", "containerization", False, ANALYSIS_MODES, None, 10, True),
    _definition("deployment_config", "Deployment configuration", "readiness", "deployment", False, ANALYSIS_MODES, None, 10, True),
    _definition("configuration_security", "Configuration and secrets", "readiness", "configuration_security", False, ANALYSIS_MODES, None, 10, True),
    _definition("observability", "Observability signals", "readiness", "observability", False, ANALYSIS_MODES, None, 10, True),
    _definition("release_hygiene", "Release hygiene", "readiness", "release_hygiene", False, ANALYSIS_MODES, None, 10, True),
    _definition("architecture_graph", "Architecture graph", "architecture", "architecture", False, ANALYSIS_MODES, None, 10, True),
)


def default_analysis_mode(source_type: str) -> AnalysisMode:
    if source_type == "github_url":
        return "quick_safe"
    if source_type == "local_path":
        return "deep_local"
    raise ValueError(f"Unsupported source_type: {source_type}")


def validate_analysis_mode(source_type: str, analysis_mode: str | None) -> AnalysisMode:
    mode = (analysis_mode.replace("-", "_") if isinstance(analysis_mode, str) else analysis_mode) or default_analysis_mode(source_type)
    if mode not in ANALYSIS_MODES:
        raise ValueError(f"Unsupported analysis_mode: {mode}")
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"Unsupported source_type: {source_type}")
    if source_type == "github_url" and mode == "deep_local":
        raise ValueError("deep_local analysis is only allowed for local_path. GitHub URL audits must use quick_safe.")
    return mode  # type: ignore[return-value]


def _version_for(module_name: str | None) -> tuple[bool, str | None, str | None]:
    if module_name is None:
        return True, None, None
    if importlib.util.find_spec(module_name) is None:
        return False, None, f"{module_name} is not installed in the DrRepo runtime."
    try:
        return True, importlib.metadata.version(module_name), None
    except importlib.metadata.PackageNotFoundError:
        return True, None, None


def capability_for(definition: AnalyzerDefinition) -> AnalyzerCapability:
    available, version, reason = _version_for(definition.module_name)
    return AnalyzerCapability(
        analyzer_id=definition.analyzer_id,
        display_name=definition.display_name,
        section=definition.section,
        category=definition.category,
        executes_repository_code=definition.executes_repository_code,
        supported_source_types=definition.supported_source_types,
        supported_analysis_modes=definition.supported_analysis_modes,
        available=available,
        installed_version=version,
        unavailable_reason=reason,
        default_timeout_seconds=definition.default_timeout_seconds,
        core=definition.core,
    )


def list_capabilities() -> list[AnalyzerCapability]:
    return [capability_for(definition) for definition in ANALYZERS]


def definitions_for(section: str) -> list[AnalyzerDefinition]:
    return [definition for definition in ANALYZERS if definition.section == section]


def definition_for(tool: str) -> AnalyzerDefinition | None:
    return next((definition for definition in ANALYZERS if definition.analyzer_id == tool), None)


def is_core_analyzer(tool: str) -> bool:
    definition = definition_for(tool)
    return bool(definition and definition.core)


def classify_result_outcome(result: ToolResult) -> tuple[str, str]:
    if result.status == "completed":
        if result.findings:
            return "findings_present", "verified evidence with findings"
        return "clean", "verified clean evidence"
    if result.status == "failed_to_run":
        if is_core_analyzer(result.tool):
            return "execution_failed", "audit-environment failure"
        return "execution_failed", "incomplete evidence"
    if result.status == "partial":
        return "execution_failed", "incomplete evidence"
    if result.status == "not_available":
        return "unavailable", "incomplete evidence"
    if result.status == "skipped_by_config":
        return "skipped", "incomplete evidence"
    if result.status == "not_applicable":
        return "not_applicable", "incomplete evidence"
    return "execution_failed", "incomplete evidence"


def apply_outcome_metadata(result: ToolResult) -> ToolResult:
    outcome, impact = classify_result_outcome(result)
    result.analysis_outcome = outcome
    result.evidence_impact = impact
    return result


def should_run(definition: AnalyzerDefinition, source_type: SourceType, analysis_mode: AnalysisMode) -> tuple[bool, str | None]:
    if definition.executes_repository_code and source_type == "github_url" and analysis_mode == "quick_safe":
        return False, "Skipped for remote GitHub audit safety."
    if source_type not in definition.supported_source_types:
        if definition.executes_repository_code and source_type == "github_url":
            return False, "Skipped for remote GitHub audit safety."
        return False, f"{definition.display_name} does not support source type {source_type}."
    if analysis_mode not in definition.supported_analysis_modes:
        return False, f"Skipped by analysis mode {analysis_mode}."
    return True, None


def skipped_result(definition: AnalyzerDefinition, analysis_mode: AnalysisMode, reason: str) -> ToolResult:
    outcome = "skipped_by_analysis_mode"
    if "remote GitHub audit safety" in reason:
        outcome = "skipped_for_remote_safety"
    return apply_outcome_metadata(ToolResult(
        tool=definition.analyzer_id,
        status="skipped_by_config",
        summary={"reason": reason, "outcome": outcome},
        findings=[],
        errors=[],
        execution_mode=analysis_mode,
        skipped_reason=reason,
    ))


def unavailable_reason_for(tool: str) -> str:
    capability = next((c for c in list_capabilities() if c.analyzer_id == tool), None)
    return capability.unavailable_reason if capability and capability.unavailable_reason else f"{tool} is not available."


def timed_run(
    runner: Callable[[], ToolResult],
    *,
    analysis_mode: AnalysisMode,
) -> ToolResult:
    started = time.perf_counter()
    result = runner()
    result.duration_ms = int((time.perf_counter() - started) * 1000)
    result.execution_mode = analysis_mode
    capability = next((c for c in list_capabilities() if c.analyzer_id == result.tool), None)
    if capability:
        result.tool_version = capability.installed_version
        if result.status == "not_available":
            result.unavailable_reason = capability.unavailable_reason or unavailable_reason_for(result.tool)
    return apply_outcome_metadata(result)


def capability_payload() -> dict[str, object]:
    from drrepo.execution import check_docker_capability

    docker_capability = check_docker_capability()
    return {
        "supported_analysis_modes": [
            {
                "id": "quick_safe",
                "display_name": "Quick Safe",
                "description": "Runs repository metadata, README, structure, and available static analyzers without executing target repository code.",
                "executes_repository_code": False,
                "supported_source_types": ["local_path", "github_url"],
            },
            {
                "id": "deep_local",
                "display_name": "Deep Local",
                "description": "Runs quick_safe analyzers plus pytest and coverage for local repositories. Project code may execute.",
                "executes_repository_code": True,
                "supported_source_types": ["local_path"],
            },
            {
                "id": "deep_isolated",
                "display_name": "Deep Isolated",
                "description": "Runs supported test and coverage verification inside a disposable DrRepo-controlled Docker container. Explicit opt-in only.",
                "executes_repository_code": True,
                "supported_source_types": ["local_path", "github_url"],
            },
        ],
        "supported_source_types": list(SOURCE_TYPES),
        "analyzers": [capability.to_dict() for capability in list_capabilities()],
        "docker_isolated_execution": docker_capability.to_dict(),
        "remote_execution_safety_policy": REMOTE_SAFETY_POLICY,
        "setup": {
            "analysis_extra": "analysis",
            "install_command": f'{sys.executable} -m pip install -e ".[analysis]"',
        },
    }


def mode_allows_test_execution(source_type: str, analysis_mode: str) -> bool:
    mode = validate_analysis_mode(source_type, analysis_mode)
    return (source_type == "local_path" and mode == "deep_local") or mode == "deep_isolated"
