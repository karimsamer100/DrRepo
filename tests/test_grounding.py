from drrepo.advisor.grounding import (
    build_evidence_index,
    normalize_evidence_path,
    validate_grounding,
)


def _sample_audit() -> dict[str, object]:
    return {
        "path": "C:/projects/example",
        "scoring": {
            "overall_score": 72,
            "repository_health_score": 70,
        },
        "diagnosis": {
            "repository_health": {"label": "needs_attention", "score": 70, "summary": "Needs work"},
        },
        "project_understanding": {
            "project_identity": {
                "project_type": "web_service",
                "secondary_project_types": ["cli"],
                "frameworks": ["fastapi"],
                "interfaces": ["rest_api"],
                "confidence": "medium",
            },
            "entry_points": [
                {"path": "src/main.py", "symbol": "main"},
            ],
        },
        "static_analysis": [
            {
                "tool": "ruff",
                "status": "completed",
                "findings": [
                    {
                        "code": "RUF001",
                        "message": "Ambiguous variable name",
                        "file_path": "src/main.py",
                        "line": 12,
                        "severity": "medium",
                    }
                ],
            }
        ],
        "test_analysis": [
            {
                "tool": "pytest",
                "status": "completed",
                "summary": {"passed": 5, "failed": 1},
                "findings": [
                    {"code": "PYTEST-FAILED", "message": "test failed", "severity": "high"}
                ],
            },
            {
                "tool": "coverage",
                "status": "completed",
                "summary": {"coverage_percent": 65},
                "findings": [],
            },
        ],
        "repository_analysis": [],
        "devops_readiness": {
            "blockers": [
                {"id": "NO-CI", "title": "No CI configuration", "category": "ci", "severity": "high"}
            ]
        },
        "recommendations_v2": [
            {
                "id": "ADD-TESTS",
                "title": "Add tests",
                "priority": 1,
                "severity": "high",
                "category": "testing",
                "recommendation_type": "repository_fix",
                "why_it_matters": "Confidence",
                "success_check": "pytest passes",
            }
        ],
    }


def test_valid_grounded_response_accepted():
    audit = _sample_audit()
    index = build_evidence_index(audit)
    response = {
        "summary": "The overall score is 72.",
        "profile_context": "FastAPI web service",
        "top_priorities": [
            {
                "title": "Fix pytest failure",
                "why_it_matters": "Tests are failing.",
                "evidence": ["PYTEST-FAILED"],
                "suggested_fix": "Repair the test.",
                "priority": "high",
            }
        ],
        "lower_priority_items": [
            {
                "title": "Add CI",
                "why_it_matters": "Blocker NO-CI exists.",
                "evidence": ["NO-CI"],
                "suggested_fix": "Add a workflow.",
                "priority": "medium",
            }
        ],
        "limitations": [],
        "next_steps": ["Run pytest."],
    }
    result = validate_grounding(response, index)
    assert result["valid"] is True
    assert result["checked_claims"] > 0


def test_unknown_finding_rejected():
    audit = _sample_audit()
    index = build_evidence_index(audit)
    response = {
        "summary": "x",
        "profile_context": "x",
        "top_priorities": [
            {
                "title": "Fix unknown",
                "why_it_matters": "x",
                "evidence": ["UNKNOWN-CODE"],
                "suggested_fix": "x",
                "priority": "high",
            }
        ],
        "lower_priority_items": [],
        "limitations": [],
        "next_steps": [],
    }
    result = validate_grounding(response, index)
    assert result["valid"] is False
    assert any("UNKNOWN-CODE" in v for v in result["violations"])


def test_unknown_analyzer_rejected():
    audit = _sample_audit()
    index = build_evidence_index(audit)
    response = {
        "summary": "x",
        "profile_context": "x",
        "top_priorities": [
            {
                "title": "mypy found issues",
                "why_it_matters": "x",
                "evidence": [],
                "suggested_fix": "x",
                "priority": "high",
            }
        ],
        "lower_priority_items": [],
        "limitations": [],
        "next_steps": [],
    }
    result = validate_grounding(response, index)
    assert result["valid"] is False
    assert "unknown_analyzer_id" in result["violation_codes"]


def test_unknown_file_path_rejected():
    audit = _sample_audit()
    index = build_evidence_index(audit)
    response = {
        "summary": "x",
        "profile_context": "x",
        "top_priorities": [
            {
                "title": "Fix",
                "why_it_matters": "x",
                "evidence": ["src/missing.py"],
                "suggested_fix": "x",
                "priority": "high",
            }
        ],
        "lower_priority_items": [],
        "limitations": [],
        "next_steps": [],
    }
    result = validate_grounding(response, index)
    assert result["valid"] is False
    assert any("src/missing.py" in v for v in result["violations"])


def test_traversal_and_absolute_path_rejected():
    assert normalize_evidence_path("../etc/passwd") is None
    assert normalize_evidence_path("/etc/passwd") is None
    assert normalize_evidence_path("C:/Windows/system.ini") is None
    assert normalize_evidence_path("src/../main.py") is None


def test_windows_path_normalization_works():
    assert normalize_evidence_path("src\\main.py") == "src/main.py"
    assert normalize_evidence_path(".\\src\\main.py") == "src/main.py"


def test_invalid_line_reference_rejected():
    audit = _sample_audit()
    index = build_evidence_index(audit)
    response = {
        "summary": "x",
        "profile_context": "x",
        "top_priorities": [
            {
                "title": "Fix",
                "why_it_matters": "x",
                "evidence": ["src/main.py:99"],
                "suggested_fix": "x",
                "priority": "high",
            }
        ],
        "lower_priority_items": [],
        "limitations": [],
        "next_steps": [],
    }
    result = validate_grounding(response, index)
    assert result["valid"] is False
    assert any("src/main.py:99" in v for v in result["violations"])


def test_score_contradiction_rejected():
    audit = _sample_audit()
    index = build_evidence_index(audit)
    response = {
        "summary": "The overall score is 95.",
        "profile_context": "x",
        "top_priorities": [],
        "lower_priority_items": [],
        "limitations": [],
        "next_steps": [],
    }
    result = validate_grounding(response, index)
    assert result["valid"] is False
    assert any("score" in v.lower() for v in result["violations"])


def test_verdict_contradiction_rejected():
    audit = _sample_audit()
    index = build_evidence_index(audit)
    response = {
        "summary": "The verdict is healthy.",
        "profile_context": "x",
        "top_priorities": [],
        "lower_priority_items": [],
        "limitations": [],
        "next_steps": [],
    }
    result = validate_grounding(response, index)
    assert result["valid"] is False
    assert any("verdict" in v.lower() for v in result["violations"])


def test_pytest_contradiction_rejected():
    audit = _sample_audit()
    index = build_evidence_index(audit)
    response = {
        "summary": "All tests passed.",
        "profile_context": "x",
        "top_priorities": [],
        "lower_priority_items": [],
        "limitations": [],
        "next_steps": [],
    }
    result = validate_grounding(response, index)
    assert result["valid"] is False
    assert any("pytest" in v.lower() for v in result["violations"])


def test_coverage_contradiction_rejected():
    audit = _sample_audit()
    index = build_evidence_index(audit)
    response = {
        "summary": "Coverage is 90%.",
        "profile_context": "x",
        "top_priorities": [],
        "lower_priority_items": [],
        "limitations": [],
        "next_steps": [],
    }
    result = validate_grounding(response, index)
    assert result["valid"] is False
    assert any("coverage" in v.lower() for v in result["violations"])


def test_invented_framework_interface_entry_point_rejected():
    audit = _sample_audit()
    index = build_evidence_index(audit)
    framework_response = {
        "summary": "Use Django as the framework.",
        "profile_context": "x",
        "top_priorities": [],
        "lower_priority_items": [],
        "limitations": [],
        "next_steps": [],
    }
    interface_response = {
        "summary": "Expose a GraphQL interface.",
        "profile_context": "x",
        "top_priorities": [],
        "lower_priority_items": [],
        "limitations": [],
        "next_steps": [],
    }
    entry_point_response = {
        "summary": "The entry point is app/server.py.",
        "profile_context": "x",
        "top_priorities": [],
        "lower_priority_items": [],
        "limitations": [],
        "next_steps": [],
    }

    framework_result = validate_grounding(framework_response, index)
    interface_result = validate_grounding(interface_response, index)
    entry_point_result = validate_grounding(entry_point_response, index)

    assert framework_result["valid"] is False
    assert "invented_framework" in framework_result["violation_codes"]
    assert interface_result["valid"] is False
    assert "invented_interface" in interface_result["violation_codes"]
    assert entry_point_result["valid"] is False
    assert "invented_entry_point" in entry_point_result["violation_codes"]


def test_unknown_blocker_rejected():
    audit = _sample_audit()
    index = build_evidence_index(audit)
    response = {
        "summary": "x",
        "profile_context": "x",
        "top_priorities": [
            {
                "title": "Fix",
                "why_it_matters": "x",
                "evidence": ["NO-DOCKER"],
                "suggested_fix": "x",
                "priority": "high",
            }
        ],
        "lower_priority_items": [],
        "limitations": [],
        "next_steps": [],
    }
    result = validate_grounding(response, index)
    assert result["valid"] is False
    assert any("NO-DOCKER" in v for v in result["violations"])


def test_unknown_recommendation_rejected():
    audit = _sample_audit()
    index = build_evidence_index(audit)
    response = {
        "summary": "x",
        "profile_context": "x",
        "top_priorities": [
            {
                "title": "Fix",
                "why_it_matters": "x",
                "evidence": ["ADD-DOCS"],
                "suggested_fix": "x",
                "priority": "high",
            }
        ],
        "lower_priority_items": [],
        "limitations": [],
        "next_steps": [],
    }
    result = validate_grounding(response, index)
    assert result["valid"] is False
    assert any("ADD-DOCS" in v for v in result["violations"])


def test_valid_references_counted():
    audit = _sample_audit()
    index = build_evidence_index(audit)
    response = {
        "summary": "x",
        "profile_context": "x",
        "top_priorities": [
            {
                "title": "Fix",
                "why_it_matters": "x",
                "evidence": ["RUF001", "src/main.py", "src/main.py:12", "NO-CI", "ADD-TESTS"],
                "suggested_fix": "x",
                "priority": "high",
            }
        ],
        "lower_priority_items": [],
        "limitations": [],
        "next_steps": [],
    }
    result = validate_grounding(response, index)
    assert result["valid"] is True
    assert result["validated_references"] >= 1


def test_safe_violation_output():
    audit = _sample_audit()
    index = build_evidence_index(audit)
    response = {
        "summary": "x",
        "profile_context": "x",
        "top_priorities": [
            {
                "title": "Fix",
                "why_it_matters": "x",
                "evidence": ["src/main.py:99"],
                "suggested_fix": "x",
                "priority": "high",
            }
        ],
        "lower_priority_items": [],
        "limitations": [],
        "next_steps": [],
    }
    result = validate_grounding(response, index)
    assert not result["valid"]
    assert result["status"] == "rejected"
    assert "unsupported_line_reference" in result["violation_codes"]
    assert all(isinstance(v, str) for v in result["violations"])
    assert not any("C:/" in v for v in result["violations"])
    assert not any("\\" in v for v in result["violations"])


def test_normalize_evidence_path_rejects_host_temp_paths():
    assert normalize_evidence_path("C:/Users/Admin/AppData/Local/Temp/repo/src/main.py") is None
    assert normalize_evidence_path("/tmp/repo/src/main.py") is None


def test_audit_root_absolute_suffix_is_stripped():
    audit_root = "C:/projects/example"
    assert normalize_evidence_path("C:/projects/example/src/main.py", audit_root) == "src/main.py"
    assert normalize_evidence_path("C:/projects/example/src/main.py", "C:/other") is None
