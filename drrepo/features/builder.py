from __future__ import annotations

from typing import Any, Dict, List

from .schema import FEATURE_SCHEMA_VERSION, FEATURE_FIELDS


def _find_tool(tools: List[dict], name: str) -> dict:
    for t in tools or []:
        if t.get("tool") == name:
            return t
    return {"tool": name, "status": "not_available", "summary": {}, "findings": []}


def _safe_get(d: dict, *path, default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(p, default)
    return cur


def build_feature_row(audit: Dict[str, Any]) -> Dict[str, Any]:
    # Ensure audit is a dict
    if not isinstance(audit, dict):
        audit = {}

    metadata = audit.get("metadata", {}) or {}

    static_analysis = audit.get("static_analysis", []) or []
    test_analysis = audit.get("test_analysis", []) or []
    repository_analysis = audit.get("repository_analysis", []) or []
    scoring = audit.get("scoring", {}) or {}
    diagnosis = audit.get("diagnosis", {}) or {}
    remediation = audit.get("remediation_suggestions", []) or []

    # metadata mappings
    total_files = int(metadata.get("total_files") or 0)
    total_dirs = int(metadata.get("total_directories") or metadata.get("total_dirs") or 0)
    python_files = int(metadata.get("python_files") or 0)
    test_files = int(metadata.get("test_files") or 0)
    non_python_files = metadata.get("non_python_files")
    if non_python_files is None:
        non_python_files = max(0, total_files - python_files)
    else:
        non_python_files = int(non_python_files)

    has_tests = bool(metadata.get("has_tests", False))
    has_readme = bool(metadata.get("has_readme", False))
    has_docs = bool(metadata.get("has_docs", False))
    dependency_files = audit.get("dependency_files", []) or metadata.get("dependency_files", []) or []
    has_dependency_file = bool(dependency_files) or bool(metadata.get("has_requirements")) or bool(metadata.get("has_pyproject"))
    has_gitignore = bool(metadata.get("has_gitignore", False))
    has_env_example = bool(metadata.get("has_env_example", False))
    has_dockerfile = bool(metadata.get("has_dockerfile", False))
    has_ci = bool(metadata.get("has_ci", False))

    # static analyzers
    ruff = _find_tool(static_analysis, "ruff")
    bandit = _find_tool(static_analysis, "bandit")
    radon = _find_tool(static_analysis, "radon")

    ruff_available = ruff.get("status") != "not_available"
    ruff_findings_count = len(ruff.get("findings") or [])

    bandit_available = bandit.get("status") != "not_available"
    bandit_findings = bandit.get("findings") or []
    bandit_findings_count = len(bandit_findings)
    bandit_high_or_critical_count = sum(1 for f in bandit_findings if (f.get("severity") or "").lower() in {"high", "critical"})

    radon_available = radon.get("status") != "not_available"
    radon_findings_count = len(radon.get("findings") or [])
    radon_average_complexity = _safe_get(radon, "summary", "average_complexity", default=0) or 0

    # test analyzers
    pytest_tool = _find_tool(test_analysis, "pytest")
    coverage_tool = _find_tool(test_analysis, "coverage")

    pytest_available = pytest_tool.get("status") != "not_available"
    pytest_passed = int(_safe_get(pytest_tool, "summary", "passed", default=0) or 0)
    pytest_failed_count = int(_safe_get(pytest_tool, "summary", "failed", default=0) or 0)
    pytest_error_count = int(_safe_get(pytest_tool, "summary", "errors", default=0) or 0)

    coverage_available = coverage_tool.get("status") == "completed"
    coverage_percent = float(_safe_get(coverage_tool, "summary", "coverage_percent", default=0) or 0)

    # repository analysis
    readme_tool = _find_tool(repository_analysis, "readme")
    structure_tool = _find_tool(repository_analysis, "structure")
    readme_findings_count = len(readme_tool.get("findings") or [])
    structure_findings_count = len(structure_tool.get("findings") or [])

    # scoring
    overall_score = scoring.get("overall_score") or scoring.get("overall") or 0
    repository_health_score = scoring.get("repository_health_score") or 0
    portfolio_readiness_score = scoring.get("portfolio_readiness_score") or 0
    categories = scoring.get("categories") or {}
    category_code_quality = categories.get("code_quality") or 0
    category_testing = categories.get("testing") or 0
    category_security = categories.get("security") or 0
    category_maintainability = categories.get("maintainability") or 0
    category_documentation = categories.get("documentation") or 0
    category_structure = categories.get("structure") or 0

    hard_flags_count = len(diagnosis.get("hard_flags") or [])
    limitations_count = len(diagnosis.get("limitations") or [])
    remediation_suggestions_count = len(remediation or [])

    # Build flat row
    row: Dict[str, Any] = {"schema_version": FEATURE_SCHEMA_VERSION}
    for f in FEATURE_FIELDS:
        row[f] = 0 if isinstance(0, int) else None

    # assign values
    row.update(
        {
            "total_files": total_files,
            "total_dirs": total_dirs,
            "python_files": python_files,
            "test_files": test_files,
            "non_python_files": non_python_files,
            "has_tests": bool(has_tests),
            "has_readme": bool(has_readme),
            "has_docs": bool(has_docs),
            "has_dependency_file": bool(has_dependency_file),
            "has_gitignore": bool(has_gitignore),
            "has_env_example": bool(has_env_example),
            "has_dockerfile": bool(has_dockerfile),
            "has_ci": bool(has_ci),
            "ruff_available": bool(ruff_available),
            "ruff_findings_count": int(ruff_findings_count),
            "bandit_available": bool(bandit_available),
            "bandit_findings_count": int(bandit_findings_count),
            "bandit_high_or_critical_count": int(bandit_high_or_critical_count),
            "radon_available": bool(radon_available),
            "radon_findings_count": int(radon_findings_count),
            "radon_average_complexity": float(radon_average_complexity),
            "pytest_available": bool(pytest_available),
            "pytest_passed": int(pytest_passed),
            "pytest_failed_count": int(pytest_failed_count),
            "pytest_error_count": int(pytest_error_count),
            "coverage_available": bool(coverage_available),
            "coverage_percent": float(coverage_percent),
            "readme_findings_count": int(readme_findings_count),
            "structure_findings_count": int(structure_findings_count),
            "overall_score": int(overall_score),
            "repository_health_score": int(repository_health_score),
            "portfolio_readiness_score": int(portfolio_readiness_score),
            "category_code_quality": int(category_code_quality),
            "category_testing": int(category_testing),
            "category_security": int(category_security),
            "category_maintainability": int(category_maintainability),
            "category_documentation": int(category_documentation),
            "category_structure": int(category_structure),
            "hard_flags_count": int(hard_flags_count),
            "limitations_count": int(limitations_count),
            "remediation_suggestions_count": int(remediation_suggestions_count),
        }
    )

    return row
