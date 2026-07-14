from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set


@dataclass
class ToolFinding:
    tool: str
    message: str
    file_path: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    severity: Optional[str] = None
    code: Optional[str] = None

    def __post_init__(self) -> None:
        # Validate numeric positions if provided
        if self.line is not None and self.line < 1:
            raise ValueError("line must be >= 1 if provided")
        if self.column is not None and self.column < 1:
            raise ValueError("column must be >= 1 if provided")


@dataclass
class ToolResult:
    tool: str
    status: str
    summary: Dict[str, Any] = field(default_factory=dict)
    findings: List[ToolFinding] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    raw_output: Optional[str] = None
    duration_ms: Optional[int] = None
    execution_mode: Optional[str] = None
    skipped_reason: Optional[str] = None
    unavailable_reason: Optional[str] = None
    tool_version: Optional[str] = None
    analysis_outcome: Optional[str] = None
    evidence_impact: Optional[str] = None

    def __post_init__(self) -> None:
        if self.status not in allowed_statuses():
            raise ValueError(f"invalid status: {self.status}")


def allowed_statuses() -> Set[str]:
    return {
        "completed",
        "not_available",
        "not_applicable",
        "skipped_by_config",
        "failed_to_run",
        "partial",
    }


def tool_finding_to_dict(finding: ToolFinding) -> Dict[str, Any]:
    return {
        "tool": finding.tool,
        "message": finding.message,
        "file_path": finding.file_path,
        "line": finding.line,
        "column": finding.column,
        "severity": finding.severity,
        "code": finding.code,
    }


def tool_result_to_dict(result: ToolResult) -> Dict[str, Any]:
    return {
        "tool": result.tool,
        "status": result.status,
        "summary": result.summary,
        "findings": [tool_finding_to_dict(f) for f in result.findings],
        "errors": list(result.errors),
        "raw_output": result.raw_output,
        "duration_ms": result.duration_ms,
        "execution_mode": result.execution_mode,
        "skipped_reason": result.skipped_reason,
        "unavailable_reason": result.unavailable_reason,
        "tool_version": result.tool_version,
        "analysis_outcome": result.analysis_outcome,
        "evidence_impact": result.evidence_impact,
    }


def make_tool_result(tool: str, status: str, **kwargs: Any) -> ToolResult:
    return ToolResult(tool=tool, status=status, **kwargs)
