from copy import deepcopy

from drrepo.advisor.llm_contract import (
    LLM_ADVISOR_CONTRACT_VERSION,
    build_fallback_advisor_response,
    build_llm_advisor_payload,
    get_llm_advisor_output_schema,
    validate_llm_advisor_response,
)
from drrepo.advisor.priorities import build_profiled_action_plan


def _sample_audit() -> dict[str, object]:
    return {
        "scoring": {
            "overall_score": 72,
            "repository_health_score": 68,
            "portfolio_readiness_score": 70,
            "categories": {"documentation": 60, "testing": 50},
        },
        "diagnosis": {
            "repository_health": {"label": "needs_attention", "score": 72, "summary": "Needs work"},
            "hard_flags": ["TESTS_FAILING"],
            "limitations": ["Coverage evidence was unavailable."],
        },
        "static_analysis": [{"tool": "ruff", "status": "completed", "summary": {"issues": 0}, "findings": []}],
        "test_analysis": [{"tool": "pytest", "status": "completed", "summary": {"passed": 2, "failed": 1}, "findings": []}],
        "repository_analysis": [{"tool": "readme", "status": "completed", "summary": {}, "findings": []}],
    }


def _sample_plan() -> dict[str, object]:
    audit = {
        "remediation_suggestions": [
            {"title": "Fix failing tests", "message": "Tests are failing", "severity": "high", "code": "PYTEST-FAILED", "tool": "pytest"},
            {"title": "Improve README documentation", "message": "Add usage guidance", "severity": "medium", "code": "README-TOO-SHORT", "tool": "readme"},
        ],
        "diagnosis": {"hard_flags": [], "limitations": ["Coverage evidence was unavailable."]},
        "scoring": {"repository_health_score": 68},
    }
    plan = build_profiled_action_plan(audit, profile_id="student_portfolio")
    assert plan["top_actions"]
    return plan


def test_build_llm_advisor_payload_returns_contract_version_v1():
    payload = build_llm_advisor_payload(_sample_audit(), _sample_plan())
    assert payload["contract_version"] == LLM_ADVISOR_CONTRACT_VERSION


def test_build_llm_advisor_payload_includes_grounding_rules():
    payload = build_llm_advisor_payload(_sample_audit(), _sample_plan())
    assert payload["grounding_rules"]


def test_build_llm_advisor_payload_includes_selected_profile_information():
    payload = build_llm_advisor_payload(_sample_audit(), _sample_plan())
    assert payload["user_goal_profile"]["profile_id"] == "student_portfolio"
    assert payload["user_goal_profile"]["display_name"] == "Student Portfolio"


def test_build_llm_advisor_payload_includes_audit_summary_without_raw_code():
    payload = build_llm_advisor_payload(_sample_audit(), _sample_plan())
    assert payload["audit_summary"]["overall_score"] == 72
    assert payload["audit_summary"]["analyzer_statuses"]
    assert "raw_output" not in str(payload["audit_summary"])


def test_build_llm_advisor_payload_includes_profiled_top_actions():
    payload = build_llm_advisor_payload(_sample_audit(), _sample_plan())
    assert payload["profiled_action_plan"]["top_actions"]


def test_build_llm_advisor_payload_handles_missing_audit_fields_without_crashing():
    payload = build_llm_advisor_payload({}, build_profiled_action_plan({}, profile_id="student_portfolio"))
    assert payload["audit_summary"]["overall_score"] == "missing"


def test_build_llm_advisor_payload_does_not_mutate_inputs():
    audit = _sample_audit()
    plan = _sample_plan()
    audit_before = deepcopy(audit)
    plan_before = deepcopy(plan)
    _ = build_llm_advisor_payload(audit, plan)
    assert audit == audit_before
    assert plan == plan_before


def test_output_schema_includes_required_fields():
    schema = get_llm_advisor_output_schema()
    assert schema["required"] == ["summary", "profile_context", "top_priorities", "lower_priority_items", "limitations", "next_steps"]


def test_output_schema_requires_full_action_item_fields():
    schema = get_llm_advisor_output_schema()
    expected_fields = ["title", "why_it_matters", "evidence", "suggested_fix", "priority"]
    assert schema["properties"]["top_priorities"]["items"]["required"] == expected_fields
    assert schema["properties"]["lower_priority_items"]["items"]["required"] == expected_fields


def test_validate_llm_advisor_response_accepts_valid_response():
    response = {
        "summary": "Fix the highest-impact issues first.",
        "profile_context": "Student portfolio emphasis.",
        "top_priorities": [
            {
                "title": "Fix failing tests",
                "why_it_matters": "Reviewers need confidence the project works.",
                "evidence": ["PYTEST-FAILED"],
                "suggested_fix": "Repair the failing test and rerun pytest.",
                "priority": "high",
            }
        ],
        "lower_priority_items": [],
        "limitations": ["Coverage evidence was unavailable."],
        "next_steps": ["Start with Fix failing tests."],
    }
    assert validate_llm_advisor_response(response) == []


def test_validate_llm_advisor_response_rejects_non_dict_response():
    assert validate_llm_advisor_response([]) == ["response must be a dict"]


def test_validate_llm_advisor_response_rejects_missing_required_fields():
    errors = validate_llm_advisor_response({"summary": "x"})
    assert any("missing required field" in error for error in errors)


def test_validate_llm_advisor_response_rejects_invalid_action_priority():
    response = {
        "summary": "x",
        "profile_context": "y",
        "top_priorities": [
            {
                "title": "Fix failing tests",
                "why_it_matters": "Reviewers need confidence the project works.",
                "evidence": ["PYTEST-FAILED"],
                "suggested_fix": "Repair the failing test and rerun pytest.",
                "priority": "urgent",
            }
        ],
        "lower_priority_items": [],
        "limitations": [],
        "next_steps": [],
    }
    errors = validate_llm_advisor_response(response)
    assert any("priority must be one of" in error for error in errors)


def test_fallback_response_follows_schema():
    response = build_fallback_advisor_response(_sample_plan())
    assert validate_llm_advisor_response(response) == []


def test_fallback_response_uses_profiled_top_actions():
    response = build_fallback_advisor_response(_sample_plan())
    assert response["top_priorities"][0]["title"] == "Fix failing tests"


def test_fallback_response_includes_limitations():
    response = build_fallback_advisor_response(_sample_plan())
    assert response["limitations"]


def test_fallback_response_has_user_friendly_summary_when_no_top_priorities():
    plan = build_profiled_action_plan(
        {
            "remediation_suggestions": [
                {"title": "Install optional tool: bandit", "message": "Tool missing", "severity": "low", "code": "TOOL-NOT-AVAILABLE", "tool": "bandit"}
            ],
            "diagnosis": {"hard_flags": [], "limitations": ["Coverage evidence was unavailable."]},
            "scoring": {"repository_health_score": 88},
        },
        profile_id="student_portfolio",
    )
    response = build_fallback_advisor_response(plan)
    assert "this repository looks strong from the available evidence" in response["summary"].lower()
    assert "optional audit-completeness improvements" in response["summary"].lower()
    assert not any("highest-priority" in step.lower() for step in response["next_steps"])
    assert any("coverage evidence was unavailable" in limitation.lower() for limitation in response["limitations"])
