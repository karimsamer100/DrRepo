from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from ..input.resolver import resolve_local_path
from .models import ToolFinding, ToolResult


def parse_ruff_json(raw_output: str) -> ToolResult:
    tool = "ruff"
    if not raw_output or raw_output.strip() == "":
        return ToolResult(tool=tool, status="completed", summary={"issue_count": 0}, findings=[], raw_output=raw_output)

    try:
        data = json.loads(raw_output)
    except Exception as exc:  # pragma: no cover - exercised by tests
        return ToolResult(
            tool=tool,
            status="failed_to_run",
            summary={"issue_count": 0},
            findings=[],
            errors=[f"Failed to parse Ruff JSON output: {exc}"],
            raw_output=raw_output,
        )

    if not isinstance(data, list):
        return ToolResult(
            tool=tool,
            status="failed_to_run",
            summary={"issue_count": 0},
            findings=[],
            errors=["Ruff JSON output is not a list"],
            raw_output=raw_output,
        )

    findings: list[ToolFinding] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        message = item.get("message") or "Ruff issue"
        filename = item.get("filename")
        location = item.get("location") or {}
        row = location.get("row")
        col = location.get("column")

        line = row if isinstance(row, int) and row >= 1 else None
        column = col if isinstance(col, int) and col >= 1 else None

        finding = ToolFinding(
            tool=tool,
            message=message,
            file_path=filename,
            line=line,
            column=column,
            severity="info",
            code=code,
        )
        findings.append(finding)

    return ToolResult(
        tool=tool,
        status="completed",
        summary={"issue_count": len(findings)},
        findings=findings,
        raw_output=raw_output,
    )


def run_ruff(path: str | Path) -> ToolResult:
    tool = "ruff"
    try:
        resolved = resolve_local_path(path)
    except Exception as exc:  # resolver raises FileNotFoundError / NotADirectoryError
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=[str(exc)])

    cmd = ["python", "-m", "ruff", "check", str(resolved), "--output-format=json"]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except FileNotFoundError as exc:
        return ToolResult(tool=tool, status="not_available", summary={}, findings=[], errors=[str(exc)])
    except subprocess.TimeoutExpired as exc:
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=[f"Ruff timed out: {exc}"], raw_output="")
    except Exception as exc:
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=[str(exc)])

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""

    # Detect missing Ruff when Python cannot import the module
    if stderr:
        stderr_lower = stderr.lower()
        if "no module named" in stderr_lower and "ruff" in stderr_lower:
            return ToolResult(tool=tool, status="not_available", summary={}, findings=[], errors=[stderr], raw_output=stdout)

    # If stdout looks like JSON, try to parse
    if stdout.strip():
        result = parse_ruff_json(stdout)
        # If parse failed, attach stderr to errors if present
        if result.status == "failed_to_run":
            if stderr:
                result.errors = result.errors + [f"stderr: {stderr}"] if result.errors else [f"stderr: {stderr}"]
            result.raw_output = stdout
        return result

    # No stdout — treat as failure if stderr exists
    if stderr:
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=[stderr], raw_output=stdout)

    # No output at all — return completed with zero findings
    return ToolResult(tool=tool, status="completed", summary={"issue_count": 0}, findings=[], raw_output="")
