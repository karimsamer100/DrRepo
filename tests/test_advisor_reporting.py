from copy import deepcopy

from drrepo.advisor.reporting import (
    ADVISOR_REPORT_VERSION,
    build_deterministic_advisor_report,
    format_advisor_markdown_section,
    format_advisor_summary_lines,
)


def _sample_audit() -> dict:
    return {
        "scoring": {
            "overall_score": 76,
            "repository_health_score": 74,
            "portfolio_readiness_score": 72,
            "categories": {"documentation": 70, "testing": 55},
        },
        "diagnosis": {
            "repository_health": {"summary": "Needs a few fixes before it feels trustworthy."},
            "hard_flags": ["README_INCOMPLETE"],
            "limitations": ["Coverage evidence was unavailable."],
        },
        "remediation_suggestions": [
            {
                "title": "Improve README documentation",
                "message": "Add usage guidance.",
                "severity": "medium",
                "code": "README-TOO-SHORT",
                "tool": "readme",
            },
            {
                "title": "Install optional tool: bandit",
                "message": "Tool missing",
                "severity": "low",
                "code": "TOOL-NOT-AVAILABLE",
                "tool": "bandit",
            },
        ],
    }


def test_build_deterministic_advisor_report_returns_version_v1():
    report = build_deterministic_advisor_report(_sample_audit())
    assert report["advisor_report_version"] == ADVISOR_REPORT_VERSION


def test_build_deterministic_advisor_report_includes_profiled_action_plan():
    report = build_deterministic_advisor_report(_sample_audit())
    assert report["profiled_action_plan"]["profile"]["profile_id"] == "student_portfolio"


def test_build_deterministic_advisor_report_includes_advisor_response():
    report = build_deterministic_advisor_report(_sample_audit())
    assert report["advisor_response"]["top_priorities"]


def test_build_deterministic_advisor_report_includes_markdown_section():
    report = build_deterministic_advisor_report(_sample_audit())
    assert "## Context-Aware Advisor" in report["markdown_section"]


def test_build_deterministic_advisor_report_includes_summary_lines():
    report = build_deterministic_advisor_report(_sample_audit())
    assert report["summary_lines"]


def test_build_deterministic_advisor_report_does_not_mutate_input_audit():
    audit = _sample_audit()
    before = deepcopy(audit)
    _ = build_deterministic_advisor_report(audit)
    assert audit == before


def test_format_advisor_markdown_section_starts_with_context_aware_heading():
    section = format_advisor_markdown_section({"profile": {"display_name": "Student Portfolio"}}, {"summary": "x", "profile_context": "y", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []})
    assert section.startswith("## Context-Aware Advisor")


def test_markdown_section_includes_selected_profile_display_name():
    section = format_advisor_markdown_section({"profile": {"display_name": "Student Portfolio"}}, {"summary": "x", "profile_context": "y", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []})
    assert "Student Portfolio" in section


def test_markdown_section_includes_top_priorities():
    section = format_advisor_markdown_section(
        {"profile": {"display_name": "Student Portfolio"}},
        {"summary": "x", "profile_context": "y", "top_priorities": [{"title": "Fix failing tests", "why_it_matters": "", "evidence": ["PYTEST-FAILED"], "suggested_fix": "", "priority": "high"}], "lower_priority_items": [], "limitations": [], "next_steps": []},
    )
    assert "Fix failing tests" in section


def test_markdown_section_includes_lower_priority_items_when_available():
    section = format_advisor_markdown_section(
        {"profile": {"display_name": "Student Portfolio"}},
        {"summary": "x", "profile_context": "y", "top_priorities": [], "lower_priority_items": [{"title": "Install optional tool", "why_it_matters": "", "evidence": ["bandit"], "suggested_fix": "", "priority": "low"}], "limitations": [], "next_steps": []},
    )
    assert "Install optional tool" in section


def test_markdown_section_includes_limitations_when_available():
    section = format_advisor_markdown_section(
        {"profile": {"display_name": "Student Portfolio"}},
        {"summary": "x", "profile_context": "y", "top_priorities": [], "lower_priority_items": [], "limitations": ["Coverage evidence was unavailable."], "next_steps": []},
    )
    assert "Coverage evidence was unavailable." in section


def test_markdown_section_no_urgent_actions_wording_when_only_lower_priority_items():
    section = format_advisor_markdown_section(
        {"profile": {"display_name": "Student Portfolio"}},
        {"summary": "x", "profile_context": "y", "top_priorities": [], "lower_priority_items": [{"title": "Install optional tool", "why_it_matters": "", "evidence": ["bandit"], "suggested_fix": "", "priority": "low"}], "limitations": [], "next_steps": []},
    )
    assert "No urgent profile-specific actions were identified from the available evidence." in section


def test_summary_lines_use_lower_priority_item_count_instead_of_generic_label():
    lines = format_advisor_summary_lines(
        {"profile": {"display_name": "Student Portfolio"}},
        {"summary": "x", "profile_context": "y", "top_priorities": [], "lower_priority_items": [{"title": "Install optional tool", "why_it_matters": "", "evidence": ["bandit"], "suggested_fix": "", "priority": "low"}], "limitations": [], "next_steps": []},
    )
    assert any(line.startswith("Lower-priority items: 1 optional") for line in lines)


def test_summary_lines_do_not_include_vague_lower_priority_present():
    lines = format_advisor_summary_lines(
        {"profile": {"display_name": "Student Portfolio"}},
        {"summary": "x", "profile_context": "y", "top_priorities": [], "lower_priority_items": [{"title": "Install optional tool", "why_it_matters": "", "evidence": ["bandit"], "suggested_fix": "", "priority": "low"}], "limitations": [], "next_steps": []},
    )
    assert not any("Lower priority: present" in line for line in lines)


def test_summary_lines_include_limitations_count_when_available():
    lines = format_advisor_summary_lines(
        {"profile": {"display_name": "Student Portfolio"}},
        {"summary": "x", "profile_context": "y", "top_priorities": [], "lower_priority_items": [], "limitations": ["Coverage evidence was unavailable."], "next_steps": []},
    )
    assert any(line.startswith("Evidence limitations:") for line in lines)


def test_summary_lines_respect_max_lines():
    lines = format_advisor_summary_lines({"profile": {"display_name": "Student Portfolio"}}, {"summary": "x", "profile_context": "y", "top_priorities": [{"title": "A"}, {"title": "B"}], "lower_priority_items": [], "limitations": [], "next_steps": []}, max_lines=2)
    assert len(lines) <= 2


def test_summary_lines_return_empty_for_non_positive_max_lines():
    assert format_advisor_summary_lines({}, {}, max_lines=0) == []


def test_empty_no_action_response_is_handled_gracefully():
    section = format_advisor_markdown_section({}, {"summary": "x", "profile_context": "y", "top_priorities": [], "lower_priority_items": [], "limitations": [], "next_steps": []})
    assert "No urgent profile-specific actions were identified from the available evidence." in section


def test_student_portfolio_report_deprioritizes_low_risk_optional_tooling_when_appropriate():
    report = build_deterministic_advisor_report(_sample_audit(), profile_id="student_portfolio")
    markdown = report["markdown_section"]
    assert "Install optional tool" in markdown or "bandit" in markdown
