from copy import deepcopy

import pytest

from drrepo.advisor.api_schema import (
    ADVISOR_API_RESPONSE_VERSION,
    build_advisor_api_response,
    validate_advisor_api_response,
)


def _sample_audit() -> dict[str, object]:
    return {
        "status": "ok",
        "metadata": {"path": "C:/repo", "total_files": 10, "python_files": 7},
        "scoring": {
            "overall_score": 84,
            "repository_health_score": 80,
            "portfolio_readiness_score": 78,
            "categories": {"documentation": 70, "testing": 60},
        },
        "diagnosis": {
            "repository_health": {"summary": "Healthy overall."},
            "hard_flags": [],
            "limitations": ["Coverage evidence was unavailable."],
            "summary": "Healthy overall.",
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


def test_build_advisor_api_response_returns_response_version_v1():
    response = build_advisor_api_response(_sample_audit())
    assert response["response_version"] == ADVISOR_API_RESPONSE_VERSION


def test_response_validates_with_no_errors_for_normal_audit():
    response = build_advisor_api_response(_sample_audit())
    assert validate_advisor_api_response(response) == []


def test_response_includes_repository_path_and_status():
    response = build_advisor_api_response(_sample_audit())
    assert response["repository"]["path"] == "C:/repo"
    assert response["repository"]["status"] == "ok"


def test_response_includes_scores():
    response = build_advisor_api_response(_sample_audit())
    assert response["scores"]["overall_score"] == 84
    assert response["scores"]["repository_health_score"] == 80


def test_response_includes_diagnosis():
    response = build_advisor_api_response(_sample_audit())
    assert response["diagnosis"]["summary"] == "Healthy overall."


def test_response_includes_advisor_object():
    response = build_advisor_api_response(_sample_audit())
    assert response["advisor"]["summary"]
    assert response["advisor"]["top_priorities"]


def test_response_includes_markdown_section_and_summary_lines():
    response = build_advisor_api_response(_sample_audit())
    assert response["reports"]["markdown_section"].startswith("## Context-Aware Advisor")
    assert response["reports"]["summary_lines"]


def test_response_excludes_prompt_bundle_by_default():
    response = build_advisor_api_response(_sample_audit())
    assert "prompt_bundle" not in response


def test_response_includes_prompt_bundle_when_requested():
    response = build_advisor_api_response(_sample_audit(), include_prompt_bundle=True)
    assert "prompt_bundle" in response


def test_debug_prompt_bundle_flag_matches_prompt_bundle_presence():
    response = build_advisor_api_response(_sample_audit())
    assert response["debug"]["prompt_bundle_included"] is False

    with_bundle = build_advisor_api_response(_sample_audit(), include_prompt_bundle=True)
    assert with_bundle["debug"]["prompt_bundle_included"] is True


def test_missing_audit_fields_produce_partial_status_but_validate_structurally():
    response = build_advisor_api_response({})
    assert response["status"] == "partial"
    assert validate_advisor_api_response(response) == []


def test_invalid_profile_id_raises_value_error():
    with pytest.raises(ValueError):
        build_advisor_api_response(_sample_audit(), profile_id="bad_profile")


def test_build_advisor_api_response_does_not_mutate_input_audit():
    audit = _sample_audit()
    before = deepcopy(audit)
    _ = build_advisor_api_response(audit)
    assert audit == before


def test_output_is_deterministic_for_same_input():
    audit = _sample_audit()
    first = build_advisor_api_response(audit, profile_id="student_portfolio")
    second = build_advisor_api_response(audit, profile_id="student_portfolio")
    assert first == second


def test_validate_advisor_api_response_rejects_non_dict():
    assert validate_advisor_api_response([]) == ["response must be a dict"]


def test_validate_advisor_api_response_rejects_missing_required_keys():
    response = build_advisor_api_response(_sample_audit())
    response.pop("advisor")
    assert any("missing required key" in error for error in validate_advisor_api_response(response))


def test_validate_advisor_api_response_rejects_invalid_status():
    response = build_advisor_api_response(_sample_audit())
    response["status"] = "bad"
    assert any("status must be" in error for error in validate_advisor_api_response(response))


def test_validate_advisor_api_response_rejects_prompt_bundle_mismatch():
    response = build_advisor_api_response(_sample_audit(), include_prompt_bundle=True)
    response["debug"]["prompt_bundle_included"] = False
    errors = validate_advisor_api_response(response)
    assert any("prompt_bundle_included" in error for error in errors)
