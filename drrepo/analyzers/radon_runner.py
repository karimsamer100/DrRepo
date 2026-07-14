from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from ..input.resolver import resolve_local_path
from .models import ToolFinding, ToolResult


RADON_FINDING_RANKS = {"C", "D", "E", "F"}


def parse_radon_cc_json(raw_output: str) -> ToolResult:
    tool = "radon"
    if not raw_output or raw_output.strip() == "":
        return ToolResult(
            tool=tool,
            status="completed",
            summary={"block_count": 0, "max_complexity": 0, "average_complexity": 0},
            findings=[],
            raw_output=raw_output,
        )

    try:
        data = json.loads(raw_output)
    except Exception as exc:
        return ToolResult(
            tool=tool,
            status="failed_to_run",
            summary={"block_count": 0, "max_complexity": 0, "average_complexity": 0},
            findings=[],
            errors=[f"Failed to parse Radon JSON output: {exc}"],
            raw_output=raw_output,
        )

    if not isinstance(data, dict):
        return ToolResult(
            tool=tool,
            status="failed_to_run",
            summary={"block_count": 0, "max_complexity": 0, "average_complexity": 0},
            findings=[],
            errors=["Radon JSON output is not an object/dict"],
            raw_output=raw_output,
        )

    findings: list[ToolFinding] = []
    total = 0
    sum_complexity = 0
    max_complexity = 0
    parse_errors: list[str] = []

    for file_path, blocks in data.items():
        if not isinstance(blocks, list):
            error_message = blocks.get("error") if isinstance(blocks, dict) else None
            reason = str(error_message or "Radon file entry is not a block list")
            parse_errors.append(f"{file_path}: {reason}")
            findings.append(
                ToolFinding(
                    tool=tool,
                    message=f"Radon could not parse {file_path}: {reason}",
                    file_path=str(file_path),
                    severity="medium",
                    code="RADON-PARSE-ERROR",
                )
            )
            continue
        for blk in blocks:
            if not isinstance(blk, dict):
                continue
            typ = blk.get("type")
            rank = blk.get("rank")
            name = blk.get("name")
            lineno = blk.get("lineno")
            col_offset = blk.get("col_offset")
            complexity = blk.get("complexity")

            if isinstance(complexity, (int, float)):
                comp = int(complexity)
            else:
                comp = 0

            total += 1
            sum_complexity += comp
            if comp > max_complexity:
                max_complexity = comp

            line = lineno if isinstance(lineno, int) and lineno >= 1 else None
            column = None
            if isinstance(col_offset, int) and col_offset >= 0:
                column = col_offset + 1

            if str(rank).upper() in RADON_FINDING_RANKS:
                message = f"{typ} {name} has complexity {comp} (rank {rank})"
                finding = ToolFinding(
                    tool=tool,
                    message=message,
                    file_path=file_path,
                    line=line,
                    column=column,
                    severity=rank,
                    code="RADON-CC",
                )
                findings.append(finding)

    average = sum_complexity / total if total > 0 else 0

    status = "partial" if parse_errors else "completed"
    return ToolResult(
        tool=tool,
        status=status,
        summary={
            "block_count": total,
            "finding_count": len(findings),
            "parse_error_count": len(parse_errors),
            "max_complexity": max_complexity,
            "average_complexity": average,
        },
        findings=findings,
        errors=parse_errors,
        raw_output=raw_output,
    )


def run_radon(path: str | Path) -> ToolResult:
    tool = "radon"
    try:
        resolved = resolve_local_path(path)
    except Exception as exc:
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=[str(exc)])

    cmd = [sys.executable, "-m", "radon", "cc", str(resolved), "-j"]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except FileNotFoundError as exc:
        return ToolResult(tool=tool, status="not_available", summary={}, findings=[], errors=[str(exc)])
    except subprocess.TimeoutExpired as exc:
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=[f"Radon timed out: {exc}"], raw_output="")
    except Exception as exc:
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=[str(exc)])

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""

    if stderr:
        stderr_lower = stderr.lower()
        if "no module named" in stderr_lower and "radon" in stderr_lower:
            return ToolResult(tool=tool, status="not_available", summary={}, findings=[], errors=[stderr], raw_output=stdout)

    if stdout.strip():
        result = parse_radon_cc_json(stdout)
        if result.status == "failed_to_run":
            if stderr:
                result.errors = result.errors + [f"stderr: {stderr}"] if result.errors else [f"stderr: {stderr}"]
            result.raw_output = stdout
        return result

    if stderr:
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=[stderr], raw_output=stdout)

    return ToolResult(tool=tool, status="completed", summary={"block_count": 0, "max_complexity": 0, "average_complexity": 0}, findings=[], raw_output="")
