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


def build_audit(path: str | Path) -> Dict[str, Any]:
    """Build the full audit dictionary for the given path.

    This function resolves the path, scans the repository, runs analyzers,
    computes scoring, and returns the final audit dict without printing.
    It intentionally does not catch broad exceptions so callers (CLI/tests)
    can handle them consistently.
    """
    resolved = resolve_local_path(path)
    scanned = scan_repository(resolved)

    root = scanned["path"]

    static_results = run_static_analyzers(root)
    test_results = run_test_analyzers(root)
    repo_results = run_repository_analyzers(root)

    scoring = score_audit_sections(static_results, test_results, repo_results)

    scanned["static_analysis"] = static_analyzers_to_dict(static_results)
    scanned["test_analysis"] = test_analyzers_to_dict(test_results)
    scanned["repository_analysis"] = repository_analyzers_to_dict(repo_results)
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
