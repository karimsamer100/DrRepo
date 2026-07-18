from copy import deepcopy

import pytest

from drrepo.advisor.llm_providers import LLMProviderResult
from drrepo.advisor.service import ADVISOR_SERVICE_VERSION, build_advisor_for_audit, build_advisor_result


def _sample_audit() -> dict[str, object]:
    return {
        "scoring": {
            "overall_score": 78,
            "repository_health_score": 74,
            "portfolio_readiness_score": 72,
            "categories": {"documentation": 70, "testing": 60},
        },
        "diagnosis": {
            "repository_health": {"summary": "Looks healthy overall."},
            "hard_flags": [],
            "limitations": ["Coverage evidence was unavailable."],
        },
        "remediation_suggestions": [
            {
                "title": "Improve README documentation",
                "message": "Add usage guidance.",
                "severity": "medium",
                "code": "README-TOO-SHORT",
                "tool": "readme",
            }
        ],
    }


def _grounded_audit() -> dict[str, object]:
    return {
        "path": "repo",
        "scoring": {"overall_score": 78, "repository_health_score": 74, "categories": {}},
        "diagnosis": {
            "repository_health": {"label": "needs_attention", "score": 74, "summary": "Needs work."},
            "hard_flags": [],
            "limitations": [],
        },
        "project_understanding": {
            "project_identity": {"project_type": "web_service", "frameworks": ["fastapi"], "interfaces": ["rest_api"]},
            "entry_points": [{"path": "src/main.py", "symbol": "main"}],
        },
        "static_analysis": [
            {
                "tool": "ruff",
                "status": "completed",
                "findings": [{"code": "RUF001", "message": "lint", "file_path": "src/main.py", "line": 12, "severity": "medium"}],
            }
        ],
        "test_analysis": [
            {"tool": "pytest", "status": "completed", "summary": {"passed": 1, "failed": 0}, "findings": []},
            {"tool": "coverage", "status": "completed", "summary": {"coverage_percent": 65}, "findings": []},
        ],
        "repository_analysis": [],
        "remediation_suggestions": [{"title": "Fix lint", "message": "lint", "severity": "medium", "code": "RUF001", "tool": "ruff"}],
        "recommendations_v2": [{"id": "FIX-LINT", "title": "Fix lint", "priority": 1}],
        "devops_readiness": {"blockers": []},
    }


def _provider_response(summary: str = "The overall score is 78.") -> dict[str, object]:
    return {
        "summary": summary,
        "profile_context": "FastAPI web service.",
        "top_priorities": [
            {
                "title": "Fix lint",
                "why_it_matters": "RUF001 is present.",
                "evidence": ["RUF001", "src/main.py:12"],
                "suggested_fix": "Address the lint finding.",
                "priority": "high",
            }
        ],
        "lower_priority_items": [],
        "limitations": [],
        "next_steps": ["Run pytest."],
    }


def test_build_advisor_result_returns_service_version_v1():
    result = build_advisor_result(_sample_audit())
    assert result["advisor_service_version"] == ADVISOR_SERVICE_VERSION


def test_build_advisor_result_includes_advisor_report():
    result = build_advisor_result(_sample_audit())
    assert "advisor_report" in result
    assert result["advisor_report"]["advisor_report_version"] == "v1"


def test_build_advisor_result_does_not_include_prompt_bundle_by_default():
    result = build_advisor_result(_sample_audit())
    assert "prompt_bundle" not in result


def test_build_advisor_result_includes_prompt_bundle_when_requested():
    result = build_advisor_result(_sample_audit(), include_prompt_bundle=True)
    assert "prompt_bundle" in result


def test_prompt_bundle_contains_system_prompt_and_user_prompt():
    result = build_advisor_result(_sample_audit(), include_prompt_bundle=True)
    bundle = result["prompt_bundle"]
    assert "system_prompt" in bundle
    assert "user_prompt" in bundle


def test_invalid_profile_id_raises_value_error():
    with pytest.raises(ValueError):
        build_advisor_result(_sample_audit(), profile_id="bad_profile")


def test_build_advisor_result_does_not_mutate_input_audit():
    audit = _sample_audit()
    before = deepcopy(audit)
    _ = build_advisor_result(audit)
    assert audit == before


def test_build_advisor_result_handles_missing_audit_fields_defensively():
    result = build_advisor_result({})
    assert result["advisor_report"]["advisor_response"]["summary"]


def test_advisor_report_shape_is_preserved_with_markdown_and_summary_lines():
    result = build_advisor_result(_sample_audit())
    report = result["advisor_report"]
    assert "markdown_section" in report
    assert "summary_lines" in report
    assert report["markdown_section"].startswith("## Context-Aware Advisor")


def test_build_advisor_result_is_deterministic_for_same_input():
    audit = _sample_audit()
    first = build_advisor_result(audit, profile_id="student_portfolio")
    second = build_advisor_result(audit, profile_id="student_portfolio")
    assert first == second


def test_build_advisor_for_audit_accepts_schema_valid_grounded_provider_output():
    result = build_advisor_for_audit(
        _grounded_audit(),
        ai=True,
        providers=[lambda prompt_bundle, fallback_response=None: LLMProviderResult(provider_id="gemini", status="ok", response=_provider_response())],
    )

    ai = result["ai"]
    assert ai["status"] == "completed"
    assert ai["source"] == "llm"
    assert ai["provider"] == "gemini"
    assert ai["grounding_result"]["valid"] is True


def test_build_advisor_for_audit_rejects_schema_valid_ungrounded_provider_output():
    result = build_advisor_for_audit(
        _grounded_audit(),
        ai=True,
        providers=[lambda prompt_bundle, fallback_response=None: LLMProviderResult(provider_id="gemini", status="ok", response=_provider_response("The overall score is 99."))],
    )

    ai = result["ai"]
    assert ai["status"] == "grounding_rejected"
    assert ai["source"] == "deterministic"
    assert ai["grounding_result"]["valid"] is False
