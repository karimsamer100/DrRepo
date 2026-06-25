from copy import deepcopy

import pytest

from drrepo.advisor.service import ADVISOR_SERVICE_VERSION, build_advisor_result


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
