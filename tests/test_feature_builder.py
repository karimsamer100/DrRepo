from drrepo.features.builder import build_feature_row
from drrepo.features.schema import FEATURE_FIELDS, validate_feature_row, FEATURE_SCHEMA_VERSION


def make_sample_audit():
    return {
        "metadata": {
            "total_files": 10,
            "total_directories": 3,
            "python_files": 6,
            "test_files": 2,
            # non_python_files omitted to test fallback
            "has_readme": True,
            "has_tests": True,
            "has_docs": False,
            "has_requirements": True,
            "has_pyproject": False,
            "has_gitignore": True,
            "has_env_example": False,
            "has_dockerfile": False,
            "has_ci": True,
        },
        "static_analysis": [
            {"tool": "ruff", "status": "completed", "summary": {}, "findings": [{"severity": "low"}]},
            {
                "tool": "bandit",
                "status": "completed",
                "summary": {},
                "findings": [
                    {"severity": "high"},
                    {"severity": "critical"},
                    {"severity": "low"},
                ],
            },
            {"tool": "radon", "status": "completed", "summary": {"average_complexity": 4.2}, "findings": [{}, {}]},
        ],
        "test_analysis": [
            {"tool": "pytest", "status": "completed", "summary": {"passed": 10, "failed": 1, "errors": 0}, "findings": []},
            {"tool": "coverage", "status": "completed", "summary": {"coverage_percent": 72.5}, "findings": []},
        ],
        "repository_analysis": [
            {"tool": "readme", "status": "completed", "summary": {}, "findings": [{}, {}]},
            {"tool": "structure", "status": "completed", "summary": {}, "findings": [{}]},
        ],
        "scoring": {
            "overall_score": 88,
            "repository_health_score": 90,
            "portfolio_readiness_score": 85,
            "categories": {
                "code_quality": 95,
                "testing": 80,
                "security": 70,
                "maintainability": 60,
                "documentation": 50,
                "structure": 40,
            },
        },
        "diagnosis": {"hard_flags": [1, 2], "limitations": [1]},
        "remediation_suggestions": [1, 2, 3],
    }


def test_build_feature_row_populated():
    audit = make_sample_audit()
    row = build_feature_row(audit)
    # schema version
    assert row.get("schema_version") == FEATURE_SCHEMA_VERSION
    # all fields present
    for f in FEATURE_FIELDS:
        assert f in row

    assert row["total_files"] == 10
    assert row["total_dirs"] == 3
    assert row["python_files"] == 6
    assert row["test_files"] == 2
    # non_python_files should fallback to total - python
    assert row["non_python_files"] == 4

    assert row["has_readme"] is True
    assert row["has_dependency_file"] is True

    assert row["ruff_available"] is True
    assert row["ruff_findings_count"] == 1

    assert row["bandit_findings_count"] == 3
    assert row["bandit_high_or_critical_count"] == 2

    assert abs(row["radon_average_complexity"] - 4.2) < 0.001

    assert row["pytest_passed"] == 10
    assert row["coverage_percent"] == 72.5

    assert row["readme_findings_count"] == 2
    assert row["structure_findings_count"] == 1

    assert row["overall_score"] == 88
    assert row["category_code_quality"] == 95

    assert row["hard_flags_count"] == 2
    assert row["remediation_suggestions_count"] == 3

    # validate passes
    assert validate_feature_row(row) == []


def test_build_feature_row_missing_keys_succeeds():
    # empty audit should not crash and should provide defaults
    row = build_feature_row({})
    assert row.get("schema_version") == FEATURE_SCHEMA_VERSION
    for f in FEATURE_FIELDS:
        assert f in row
    # numeric defaults
    assert row["total_files"] == 0
    assert row["ruff_findings_count"] == 0
    # booleans default to False
    assert row["has_readme"] is False
