from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
import tempfile
import os

from ..input.resolver import resolve_local_path
from .models import ToolResult


def parse_coverage_json(raw_output: str) -> ToolResult:
    tool = "coverage"
    if not raw_output or raw_output.strip() == "":
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=["empty coverage output"], raw_output=raw_output)

    try:
        data = json.loads(raw_output)
    except Exception as exc:
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=[f"Failed to parse coverage JSON: {exc}"], raw_output=raw_output)

    if not isinstance(data, dict) or "totals" not in data:
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=["Coverage JSON missing 'totals'"], raw_output=raw_output)

    totals = data.get("totals")
    if not isinstance(totals, dict):
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=["Coverage 'totals' is not an object"], raw_output=raw_output)

    coverage_percent = totals.get("percent_covered")
    covered_lines = totals.get("covered_lines")
    num_statements = totals.get("num_statements")
    missing_lines = totals.get("missing_lines")

    summary: dict[str, Any] = {
        "coverage_percent": coverage_percent,
        "covered_lines": covered_lines,
        "num_statements": num_statements,
        "missing_lines": missing_lines,
    }

    return ToolResult(tool=tool, status="completed", summary=summary, findings=[], raw_output=raw_output)


def run_coverage(path: str | Path) -> ToolResult:
    tool = "coverage"
    try:
        resolved = resolve_local_path(path)
    except Exception as exc:
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=[str(exc)])

    # Step 1: coverage run -m pytest
    cmd_run = ["python", "-m", "coverage", "run", "-m", "pytest", str(resolved), "-q"]
    try:
        proc_run = subprocess.run(cmd_run, capture_output=True, text=True, timeout=60)
    except FileNotFoundError as exc:
        return ToolResult(tool=tool, status="not_available", summary={}, findings=[], errors=[str(exc)])
    except subprocess.TimeoutExpired as exc:
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=[f"Coverage run timed out: {exc}"], raw_output="")
    except Exception as exc:
        return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=[str(exc)])

    stdout_run = proc_run.stdout or ""
    stderr_run = proc_run.stderr or ""

    # Detect missing coverage module
    if stderr_run:
        if "no module named" in stderr_run.lower() and "coverage" in stderr_run.lower():
            return ToolResult(tool=tool, status="not_available", summary={}, findings=[], errors=[stderr_run], raw_output=stdout_run)

    # Step 2: coverage json -> write to a temporary file (Windows-safe)
    tmp_path = None
    try:
        tf = tempfile.NamedTemporaryFile(prefix="drrepo_coverage_", suffix=".json", delete=False)
        tmp_path = tf.name
        tf.close()

        cmd_json = ["python", "-m", "coverage", "json", "-o", tmp_path]
        try:
            proc_json = subprocess.run(cmd_json, capture_output=True, text=True, timeout=60)
        except FileNotFoundError as exc:
            return ToolResult(tool=tool, status="not_available", summary={}, findings=[], errors=[str(exc)])
        except subprocess.TimeoutExpired as exc:
            return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=[f"Coverage json timed out: {exc}"], raw_output=(proc_run.stdout or ""))
        except Exception as exc:
            return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=[str(exc)], raw_output=(proc_run.stdout or ""))

        stdout_json = proc_json.stdout or ""
        stderr_json = proc_json.stderr or ""

        if stderr_json:
            if "no module named" in stderr_json.lower() and "coverage" in stderr_json.lower():
                return ToolResult(tool=tool, status="not_available", summary={}, findings=[], errors=[stderr_json], raw_output=stdout_json)

        # Read the JSON content from the temporary file
        try:
            with open(tmp_path, "r", encoding="utf-8") as fh:
                file_content = fh.read()
        except Exception as exc:
            # Could not read the json file
            errs = [f"Failed to read coverage json file: {exc}"]
            if stderr_json:
                errs.append(f"stderr: {stderr_json}")
            if stderr_run:
                errs.append(f"coverage run stderr: {stderr_run}")
            return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=errs, raw_output=(proc_run.stdout or ""))

        # Parse the JSON output
        result = parse_coverage_json(file_content)
        if result.status == "failed_to_run":
            # Attach stderr info if present
            errs = result.errors or []
            if 'stderr_json' in locals() and stderr_json:
                errs = errs + [f"stderr: {stderr_json}"]
            if stderr_run:
                errs = errs + [f"coverage run stderr: {stderr_run}"]
            return ToolResult(tool=tool, status="failed_to_run", summary={}, findings=[], errors=errs, raw_output=(file_content if 'file_content' in locals() else stdout_json))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    return result
