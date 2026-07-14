from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from drrepo.input.resolver import resolve_local_path
from drrepo.scanner.repository_scanner import scan_repository
from drrepo.analyzers.service import (
    run_static_analyzers,
    static_analyzers_to_dict,
)
from drrepo.analyzers.test_service import run_test_analyzers, test_analyzers_to_dict
from drrepo.analyzers.repository_service import (
    run_repository_analyzers,
    repository_analyzers_to_dict,
)
from drrepo.scoring import score_audit_sections
from drrepo.diagnosis import build_diagnosis
from drrepo.remediation.suggestions import generate_suggestions, count_suggestions_by_severity
from drrepo.analyzers.registry import validate_analysis_mode
from drrepo.environment import detect_dependency_environment


def _run_with_mode(fn, root: str | Path, *, source_type: str, analysis_mode: str):
    try:
        return fn(root, source_type=source_type, analysis_mode=analysis_mode)
    except TypeError as exc:
        if "unexpected keyword" not in str(exc):
            raise
        return fn(root)


def _run_tests_with_mode(fn, root: str | Path, *, source_type: str, analysis_mode: str, execute_tests: bool | None):
    try:
        return fn(root, source_type=source_type, analysis_mode=analysis_mode)
    except TypeError as exc:
        if "unexpected keyword" not in str(exc):
            raise
        if execute_tests is not None:
            return fn(root, execute_tests=execute_tests)
        return fn(root)


def build_audit(
    path: str | Path,
    *,
    execute_tests: bool | None = None,
    source_type: str = "local_path",
    analysis_mode: str | None = None,
) -> Dict[str, Any]:
    """Build the full audit dictionary for the given path.

    This function resolves the path, scans the repository, runs analyzers,
    computes scoring, and returns the final audit dict without printing.
    It intentionally does not catch broad exceptions so callers (CLI/tests)
    can handle them consistently.
    """
    if analysis_mode is None:
        if execute_tests is None:
            mode = validate_analysis_mode(source_type, None)
        else:
            mode = "deep_local" if execute_tests else "quick_safe"
            mode = validate_analysis_mode(source_type, mode)
    else:
        mode = validate_analysis_mode(source_type, analysis_mode)

    resolved = resolve_local_path(path)
    scanned = scan_repository(resolved)

    root = scanned["path"]

    static_results = _run_with_mode(run_static_analyzers, root, source_type=source_type, analysis_mode=mode)
    test_results = _run_tests_with_mode(
        run_test_analyzers,
        root,
        source_type=source_type,
        analysis_mode=mode,
        execute_tests=execute_tests,
    )
    repo_results = _run_with_mode(run_repository_analyzers, root, source_type=source_type, analysis_mode=mode)

    scoring = score_audit_sections(static_results, test_results, repo_results)

    scanned["static_analysis"] = static_analyzers_to_dict(static_results)
    scanned["test_analysis"] = test_analyzers_to_dict(test_results)
    scanned["repository_analysis"] = repository_analyzers_to_dict(repo_results)
    scanned["analysis"] = {
        "mode": mode,
        "source_type": source_type,
        "executes_repository_code": mode == "deep_local",
    }
    scanned["dependency_environment"] = detect_dependency_environment(root)
    scanned["scoring"] = scoring

    # Build diagnosis before remediation so future remediations can use it
    scanned["diagnosis"] = build_diagnosis(scanned)

    # Generate remediation suggestions after analyzers, scoring, and diagnosis are attached
    remediation = generate_suggestions(scanned)
    scanned["remediation_suggestions"] = remediation
    scanned["remediation_summary"] = {
        "total": len(remediation),
        "by_severity": count_suggestions_by_severity(remediation),
    }

    return scanned
