from __future__ import annotations

from typing import List, Dict, Any

FEATURE_SCHEMA_VERSION = "v1"

FEATURE_FIELDS = (
    "total_files",
    "total_dirs",
    "python_files",
    "test_files",
    "non_python_files",
    "has_tests",
    "has_readme",
    "has_docs",
    "has_dependency_file",
    "has_gitignore",
    "has_env_example",
    "has_dockerfile",
    "has_ci",
    "ruff_available",
    "ruff_findings_count",
    "bandit_available",
    "bandit_findings_count",
    "bandit_high_or_critical_count",
    "radon_available",
    "radon_findings_count",
    "radon_average_complexity",
    "pytest_available",
    "pytest_passed",
    "pytest_failed_count",
    "pytest_error_count",
    "coverage_available",
    "coverage_percent",
    "readme_findings_count",
    "structure_findings_count",
    "overall_score",
    "repository_health_score",
    "portfolio_readiness_score",
    "category_code_quality",
    "category_testing",
    "category_security",
    "category_maintainability",
    "category_documentation",
    "category_structure",
    "hard_flags_count",
    "limitations_count",
    "remediation_suggestions_count",
)


def get_feature_schema() -> Dict[str, Any]:
    return {
        "schema_version": FEATURE_SCHEMA_VERSION,
        "fields": list(FEATURE_FIELDS),
        "field_count": len(FEATURE_FIELDS),
    }


_FORBIDDEN_LABEL_KEYS = {
    "label",
    "labels",
    "target",
    "y",
    "repository_label",
    "portfolio_label",
    "readiness_label",
}


def validate_feature_row(row: object) -> List[str]:
    errors: List[str] = []
    if not isinstance(row, dict):
        errors.append("feature row must be a dict")
        return errors

    sv = row.get("schema_version")
    if sv is None:
        errors.append("missing schema_version")
    elif sv != FEATURE_SCHEMA_VERSION:
        errors.append(f"schema_version must be {FEATURE_SCHEMA_VERSION}")

    # missing fields
    for f in FEATURE_FIELDS:
        if f not in row:
            errors.append(f"missing field: {f}")

    # forbidden keys
    for fk in _FORBIDDEN_LABEL_KEYS:
        if fk in row:
            errors.append(f"forbidden key present: {fk}")

    return errors
