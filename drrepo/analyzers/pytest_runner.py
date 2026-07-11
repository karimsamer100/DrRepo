from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional

from .models import ToolFinding, ToolResult
from ..input.resolver import resolve_local_path


def _extract_failure_reason(stdout: str, stderr: str) -> str | None:
    combined = "\n".join(part for part in (stderr, stdout) if part).strip()
    if not combined:
        return None

    patterns = (
        r"(ModuleNotFoundError:[^\r\n]+)",
        r"(ImportError:[^\r\n]+)",
        r"(ERROR collecting[^\r\n]+)",
        r"(UsageError:[^\r\n]+)",
        r"(FileNotFoundError:[^\r\n]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, combined, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()

    for line in combined.splitlines():
        candidate = line.strip()
        if not candidate or candidate.startswith("="):
            continue
        if candidate.startswith("E   "):
            candidate = candidate[4:].strip()
        lower = candidate.lower()
        if any(
            marker in lower
            for marker in (
                "modulenotfounderror",
                "importerror",
                "error collecting",
                "usageerror",
                "no module named",
                "file not found",
                "fixture",
            )
        ):
            return candidate
    for line in combined.splitlines():
        candidate = line.strip()
        if candidate and not candidate.startswith("="):
            return candidate
    return None


def parse_pytest_output(stdout: str, stderr: str = "", returncode: int = 0) -> ToolResult:
    tool = "pytest"
    out = (stdout or "")
    combined = f"{stdout}\n{stderr}"
    s_out = out.lower()
    s_combined = combined.lower()

    summary = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 0,
        "returncode": returncode,
        "outcome": "unknown",
    }
    findings: list[ToolFinding] = []

    combined_lower = f"{stdout}\n{stderr}".lower()
    if "no module named pytest" in combined_lower or "no module named 'pytest'" in combined_lower:
        summary["outcome"] = "pytest_unavailable"
        return ToolResult(
            tool=tool,
            status="not_available",
            summary=summary,
            findings=[],
            errors=["Pytest was not available in this environment."],
            raw_output=stdout,
        )

    # no tests ran
    if "no tests ran" in s_combined:
        summary["outcome"] = "no_tests"
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
            reason = _extract_failure_reason(stdout, stderr) or "Unable to parse pytest output"
            reason_lower = reason.lower()
            if "error collecting" in reason_lower:
                outcome = "collection_error"
            elif any(marker in reason_lower for marker in ("modulenotfounderror", "importerror", "no module named")):
                outcome = "env_error"
            else:
                outcome = "env_error"
            summary["outcome"] = outcome
            return ToolResult(
                tool=tool,
                status="failed_to_run",
                summary=summary,
                findings=[],
                errors=[f"Pytest could not run: {reason}"],
                raw_output=stdout,
            )
        else:
            summary["outcome"] = "partial"
            return ToolResult(tool=tool, status="partial", summary=summary, findings=[], errors=["Unable to parse pytest summary"], raw_output=stdout)

    # Build findings
    if failed > 0:
        findings.append(ToolFinding(tool=tool, message=f"{failed} test(s) failed", severity="high", code="PYTEST-FAILED"))
    if errors > 0:
        findings.append(
            ToolFinding(
                tool=tool,
                message=f"{errors} test collection/runtime error(s)",
                severity="high",
                code="PYTEST-ERROR",
            )
        )

    # Status: if returncode == 0 -> completed, else completed as pytest ran but tests may have failed
    status = "completed" if returncode == 0 or (failed > 0 or errors > 0) else "completed"
    if failed > 0 and errors > 0:
        summary["outcome"] = "collection_error"
    elif failed > 0:
        summary["outcome"] = "failed_tests"
    elif errors > 0:
        summary["outcome"] = "collection_error"
    else:
        summary["outcome"] = "passed"

    return ToolResult(tool=tool, status=status, summary=summary, findings=findings, raw_output=stdout)


def run_pytest(path: str | Path) -> ToolResult:
    tool = "pytest"
    try:
        resolved = resolve_local_path(path)
    except Exception as exc:
        return ToolResult(tool=tool, status="failed_to_run", summary={"outcome": "env_error"}, findings=[], errors=[str(exc)])

    cmd = [
        "python",
        "-m",
        "pytest",
        str(resolved),
        "-q",
        "-p",
        "no:cacheprovider",
        "--ignore-glob=*pytest-cache-files-*",
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except FileNotFoundError as exc:
        return ToolResult(tool=tool, status="not_available", summary={"outcome": "pytest_unavailable"}, findings=[], errors=[str(exc)])
    except subprocess.TimeoutExpired as exc:
        return ToolResult(tool=tool, status="failed_to_run", summary={"outcome": "timeout"}, findings=[], errors=[f"Pytest timed out: {exc}"], raw_output="")
    except Exception as exc:
        return ToolResult(tool=tool, status="failed_to_run", summary={"outcome": "env_error"}, findings=[], errors=[str(exc)])

    return parse_pytest_output(proc.stdout or "", proc.stderr or "", getattr(proc, "returncode", 0))
