from copy import deepcopy

import pytest

from drrepo.advisor.profiles import get_profile
from drrepo.advisor.priorities import (
    PROFILED_PLAN_VERSION,
    build_profiled_action_plan,
    rank_remediation_suggestions,
    explain_profile_impact,
    summarize_profile_fit,
)
from tests.fixtures.synthetic_audits import healthy_audit, weak_audit


def test_build_profiled_action_plan_returns_plan_version_v1():
    audit = {"remediation_suggestions": [{"title": "Improve README", "message": "Add docs", "severity": "medium", "code": "README-TOO-SHORT"}]}
    plan = build_profiled_action_plan(audit, profile_id="student_portfolio")
    assert plan["plan_version"] == PROFILED_PLAN_VERSION


def test_build_profiled_action_plan_includes_selected_profile():
    plan = build_profiled_action_plan({}, profile_id="production_service")
    assert plan["profile"]["profile_id"] == "production_service"


def test_build_profiled_action_plan_does_not_mutate_input_audit():
    audit = {"remediation_suggestions": [{"title": "Improve README", "message": "Add docs", "severity": "medium"}]}
    before = deepcopy(audit)
    _ = build_profiled_action_plan(audit, profile_id="student_portfolio")
    assert audit == before


def test_student_portfolio_ranks_readme_above_optional_security_tooling_when_low_risk():
    suggestions = [
        {"title": "Install optional tool: bandit", "message": "Tool missing", "severity": "low", "code": "TOOL-NOT-AVAILABLE", "tool": "bandit"},
        {"title": "Improve README documentation", "message": "Add usage docs", "severity": "medium", "code": "README-TOO-SHORT"},
    ]
    ranked = rank_remediation_suggestions(suggestions, "student_portfolio")
    assert ranked[0]["title"] == "Improve README documentation"


def test_production_service_ranks_security_above_documentation_when_security_severity_is_high():
    suggestions = [
        {"title": "Improve README documentation", "message": "Add docs", "severity": "medium", "code": "README-TOO-SHORT"},
        {"title": "Review security finding", "message": "Bandit found something", "severity": "high", "code": "B101"},
    ]
    ranked = rank_remediation_suggestions(suggestions, "production_service")
    assert ranked[0]["title"] == "Review security finding"


def test_failing_tests_are_high_priority_for_all_profiles():
    suggestion = {"title": "Fix failing tests", "message": "1 failing test", "severity": "high", "code": "PYTEST-FAILED"}
    for profile_id in ["student_portfolio", "production_service"]:
        ranked = rank_remediation_suggestions([suggestion], profile_id)
        assert ranked[0]["profile_priority"] == "high"


def test_optional_missing_tools_are_low_priority_for_student_portfolio():
    suggestion = {"title": "Install optional tool: bandit", "message": "Tool missing", "severity": "low", "code": "TOOL-NOT-AVAILABLE", "tool": "bandit"}
    ranked = rank_remediation_suggestions([suggestion], "student_portfolio")
    assert ranked[0]["profile_priority"] == "low"


def test_high_critical_security_findings_are_high_priority_for_all_profiles():
    suggestion = {"title": "Review security finding", "message": "Critical", "severity": "critical", "code": "B101"}
    for profile_id in ["student_portfolio", "production_service"]:
        ranked = rank_remediation_suggestions([suggestion], profile_id)
        assert ranked[0]["profile_priority"] == "high"


def test_missing_remediation_suggestions_is_handled_gracefully():
    plan = build_profiled_action_plan({"diagnosis": {"hard_flags": []}}, profile_id="student_portfolio")
    assert "top_actions" in plan


def test_max_actions_limits_top_actions():
    suggestions = [{"title": f"Action {i}", "message": "x", "severity": "low"} for i in range(10)]
    plan = build_profiled_action_plan({"remediation_suggestions": suggestions}, profile_id="student_portfolio", max_actions=3)
    assert len(plan["top_actions"]) <= 3


def test_deprioritized_actions_contains_lower_context_actions_when_available():
    audit = {"remediation_suggestions": [{"title": "Install optional tool: bandit", "message": "Tool missing", "severity": "low", "code": "TOOL-NOT-AVAILABLE", "tool": "bandit"}]}
    plan = build_profiled_action_plan(audit, profile_id="student_portfolio")
    assert any(action["priority"] == "low" for action in plan["deprioritized_actions"])


def test_invalid_profile_id_raises_value_error():
    with pytest.raises(ValueError):
        build_profiled_action_plan({}, profile_id="bad_profile")


def test_profile_fit_summary_is_present_and_non_empty():
    plan = build_profiled_action_plan({}, profile_id="student_portfolio")
    assert plan["profile_fit_summary"]


def test_evidence_notes_mention_unavailable_evidence_when_important_sections_missing():
    plan = build_profiled_action_plan({}, profile_id="student_portfolio")
    assert any("unavailable_evidence" in note for note in plan["evidence_notes"])
