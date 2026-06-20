from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional

from .models import ToolFinding, ToolResult
from ..input.resolver import resolve_local_path


def parse_pytest_output(stdout: str, stderr: str = "", returncode: int = 0) -> ToolResult:
    tool = "pytest"
    out = (stdout or "")
    s_out = out.lower()

    summary = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0, "returncode": returncode}
    findings: list[ToolFinding] = []

    # no tests ran
    if "no tests ran" in s_out:
        return ToolResult(tool=tool, status="not_applicable", summary=summary, findings=[], raw_output=stdout)

    # patterns
    def find_int(pattern: str) -> Optional[int]:
        m = re.search(pattern, stdout)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return None
        return None

    passed = find_int(r"(\d+)\s+passed") or 0
    failed = find_int(r"(\d+)\s+failed") or 0
    skipped = find_int(r"(\d+)\s+skipped") or 0
    errors = find_int(r"(\d+)\s+error") or 0

    summary.update({"passed": passed, "failed": failed, "skipped": skipped, "errors": errors})

    # If nothing parsed and returncode != 0 -> failed_to_run
    if passed == 0 and failed == 0 and skipped == 0 and errors == 0:
        if returncode != 0:
            return ToolResult(tool=tool, status="failed_to_run", summary=summary, findings=[], errors=[stderr or "Unable to parse pytest output"], raw_output=stdout)
        else:
            return ToolResult(tool=tool, status="partial", summary=summary, findings=[], errors=["Unable to parse pytest summary"], raw_output=stdout)

    # Build findings
    if failed > 0:
        findings.append(ToolFinding(tool=tool, message=f"{failed} test(s) failed", severity="high", code="PYTEST-FAILED"))
    if errors > 0:
        findings.append(ToolFinding(tool=tool, message=f"{errors} test error(s)", severity="high", code="PYTEST-ERROR"))

    # Status: if returncode == 0 -> completed, else completed as pytest ran but tests may have failed
    status = "completed" if returncode == 0 or (failed > 0 or errors > 0) else "completed"

    return ToolResult(tool=tool, status=status, summary=summary, findings=findings, raw_output=stdout)


def run_pytest(path: str | Path) -> ToolResult:
    tool = "pytest"
    try:
        resolved = resolve_local_path(path)
    except Exception as exc:
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=[str(exc)])

    cmd = ["python", "-m", "pytest", str(resolved), "-q"]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except FileNotFoundError as exc:
        return ToolResult(tool=tool, status="not_available", summary={}, findings=[], errors=[str(exc)])
    except subprocess.TimeoutExpired as exc:
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=[f"Pytest timed out: {exc}"], raw_output="")
    except Exception as exc:
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=[str(exc)])

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    returncode = getattr(proc, "returncode", 0)

    # Detect missing pytest from stderr
    if stderr:
        stderr_lower = stderr.lower()
        if "no module named" in stderr_lower and "pytest" in stderr_lower:
            return ToolResult(tool=tool, status="not_available", summary={}, findings=[], errors=[stderr], raw_output=stdout)

    return parse_pytest_output(stdout, stderr, returncode)
