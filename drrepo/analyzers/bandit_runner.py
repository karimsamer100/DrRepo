from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from ..input.resolver import resolve_local_path
from .models import ToolFinding, ToolResult


def parse_bandit_json(raw_output: str) -> ToolResult:
    tool = "bandit"
    if not raw_output or raw_output.strip() == "":
        return ToolResult(tool=tool, status="completed", summary={"issue_count": 0}, findings=[], raw_output=raw_output)

    try:
        data = json.loads(raw_output)
    except Exception as exc:
        return ToolResult(
            tool=tool,
            status="failed_to_run",
            summary={"issue_count": 0},
            findings=[],
            errors=[f"Failed to parse Bandit JSON output: {exc}"],
            raw_output=raw_output,
        )

    if not isinstance(data, dict) or "results" not in data:
        return ToolResult(
            tool=tool,
            status="failed_to_run",
            summary={"issue_count": 0},
            findings=[],
            errors=["Bandit JSON missing 'results' list"],
            raw_output=raw_output,
        )

    results = data.get("results")
    if not isinstance(results, list):
        return ToolResult(
            tool=tool,
            status="failed_to_run",
            summary={"issue_count": 0},
            findings=[],
            errors=["Bandit 'results' is not a list"],
            raw_output=raw_output,
        )

    findings: list[ToolFinding] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        filename = item.get("filename")
        line_num = item.get("line_number")
        message = item.get("issue_text") or "Bandit issue"
        severity = item.get("issue_severity")
        test_id = item.get("test_id")

        line = line_num if isinstance(line_num, int) and line_num >= 1 else None

        finding = ToolFinding(
            tool=tool,
            message=message,
            file_path=filename,
            line=line,
            column=None,
            severity=severity,
            code=test_id,
        )
        findings.append(finding)

    return ToolResult(
        tool=tool,
        status="completed",
        summary={"issue_count": len(findings)},
        findings=findings,
        raw_output=raw_output,
    )


def run_bandit(path: str | Path) -> ToolResult:
    tool = "bandit"
    try:
        resolved = resolve_local_path(path)
    except Exception as exc:
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=[str(exc)])

    cmd = ["python", "-m", "bandit", "-r", str(resolved), "-f", "json"]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except FileNotFoundError as exc:
        return ToolResult(tool=tool, status="not_available", summary={}, findings=[], errors=[str(exc)])
    except subprocess.TimeoutExpired as exc:
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=[f"Bandit timed out: {exc}"], raw_output="")
    except Exception as exc:
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=[str(exc)])

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""

    # Detect missing Bandit from stderr
    if stderr:
        stderr_lower = stderr.lower()
        if "no module named" in stderr_lower and "bandit" in stderr_lower:
            return ToolResult(tool=tool, status="not_available", summary={}, findings=[], errors=[stderr], raw_output=stdout)

    if stdout.strip():
        result = parse_bandit_json(stdout)
        if result.status == "failed_to_run":
            if stderr:
                result.errors = result.errors + [f"stderr: {stderr}"] if result.errors else [f"stderr: {stderr}"]
            result.raw_output = stdout
        return result

    if stderr:
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=[stderr], raw_output=stdout)

    return ToolResult(tool=tool, status="completed", summary={"issue_count": 0}, findings=[], raw_output="")
