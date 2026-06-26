from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

import drrepo.cli as cli_module
from drrepo.cli import app

runner = CliRunner()


def _fake_audit() -> dict[str, object]:
    return {
        "path": "sample",
        "status": "ok",
        "metadata": {"total_files": 1, "python_files": 1},
        "scoring": {"overall_score": 95, "categories": {}},
        "diagnosis": {
            "repository_health": {"label": "healthy", "summary": "Looks good."},
            "hard_flags": [],
            "limitations": [],
        },
        "static_analysis": [],
        "test_analysis": [],
        "repository_analysis": [],
        "remediation_suggestions": [],
        "remediation_summary": {},
    }


def _fake_advisor_report(profile_display_name: str = "Student Portfolio") -> dict[str, object]:
    advisor_response = {
        "summary": "AI summary",
        "profile_context": "AI context",
        "top_priorities": [
            {
                "title": "Improve tests",
                "why_it_matters": "Raises confidence.",
                "evidence": ["tests/"],
                "suggested_fix": "Add more tests.",
                "priority": "high",
            }
        ],
        "lower_priority_items": [],
        "limitations": ["No coverage data."],
        "next_steps": ["Run the test suite."],
    }
    return {
        "advisor_response": advisor_response,
        "markdown_section": (
            "## Context-Aware Advisor\n\n"
            f"- **Profile**: {profile_display_name}\n"
            f"- **Profile context**: {advisor_response['profile_context']}\n"
            f"- **Summary**: {advisor_response['summary']}"
        ),
        "summary_lines": [
            f"Profile: {profile_display_name}",
            f"Summary: {advisor_response['summary']}",
            "Top advisor action: Improve tests",
        ],
        "profiled_action_plan": {"profile": {"display_name": profile_display_name}},
    }


def test_audit_without_ai_and_without_profile_stays_deterministic_without_router(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cli_module, "build_audit", lambda path: _fake_audit())

    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "json"])

    assert result.exit_code == 0
    assert '"advisor_report"' not in result.output
    assert '"llm_router"' not in result.output


def test_audit_with_profile_and_without_ai_remains_deterministic(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cli_module, "build_audit", lambda path: _fake_audit())

    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "json", "--profile", "student_portfolio"])

    assert result.exit_code == 0
    assert '"advisor_report"' in result.output
    assert '"llm_router"' not in result.output


def test_ai_without_profile_uses_student_portfolio(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cli_module, "build_audit", lambda path: _fake_audit())
    captured: dict[str, object] = {}

    def fake_build_advisor_result(audit, profile_id="student_portfolio", max_actions=5, include_prompt_bundle=False):
        captured["profile_id"] = profile_id
        result = {
            "advisor_service_version": "v1",
            "profile_id": profile_id,
            "advisor_report": _fake_advisor_report(),
        }
        if include_prompt_bundle:
            result["prompt_bundle"] = {"system_prompt": "sys", "user_prompt": "usr"}
        return result

    def fake_route(prompt_bundle, fallback_response):
        return {
            "router_version": "v1",
            "selected_provider_id": "gemini",
            "used_fallback": False,
            "provider_attempts": [{"provider_id": "gemini", "status": "ok"}],
            "advisor_response": {
                "summary": "AI summary",
                "profile_context": "AI context",
                "top_priorities": [],
                "lower_priority_items": [],
                "limitations": [],
                "next_steps": [],
            },
        }

    monkeypatch.setattr(cli_module, "build_advisor_result", fake_build_advisor_result)
    monkeypatch.setattr(cli_module, "route_llm_advisor_response", fake_route)

    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "summary", "--ai"])

    assert result.exit_code == 0
    assert captured["profile_id"] == "student_portfolio"
    assert "Advisor mode: AI" in result.output
    assert "Selected provider: gemini" in result.output


def test_ai_markdown_includes_context_aware_advisor_and_provider_metadata(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cli_module, "build_audit", lambda path: _fake_audit())
    monkeypatch.setattr(cli_module, "build_advisor_result", lambda *args, **kwargs: {"advisor_service_version": "v1", "profile_id": "student_portfolio", "advisor_report": _fake_advisor_report(), "prompt_bundle": {"system_prompt": "sys", "user_prompt": "usr"}})
    monkeypatch.setattr(cli_module, "route_llm_advisor_response", lambda prompt_bundle, fallback_response: {"router_version": "v1", "selected_provider_id": "gemini", "used_fallback": False, "provider_attempts": [{"provider_id": "gemini", "status": "ok"}], "advisor_response": _fake_audit()["diagnosis"] if False else _fake_advisor_report()["advisor_response"]})

    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "markdown", "--profile", "student_portfolio", "--ai"])

    assert result.exit_code == 0
    assert "Context-Aware Advisor" in result.output
    assert "Advisor provider: gemini" in result.output
    assert "Fallback used: No" in result.output


def test_ai_summary_includes_selected_provider_metadata(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cli_module, "build_audit", lambda path: _fake_audit())
    monkeypatch.setattr(cli_module, "build_advisor_result", lambda *args, **kwargs: {"advisor_service_version": "v1", "profile_id": "student_portfolio", "advisor_report": _fake_advisor_report(), "prompt_bundle": {"system_prompt": "sys", "user_prompt": "usr"}})
    monkeypatch.setattr(cli_module, "route_llm_advisor_response", lambda prompt_bundle, fallback_response: {"router_version": "v1", "selected_provider_id": "gemini", "used_fallback": False, "provider_attempts": [{"provider_id": "gemini", "status": "ok"}], "advisor_response": _fake_advisor_report()["advisor_response"]})

    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "summary", "--profile", "student_portfolio", "--ai"])

    assert result.exit_code == 0
    assert "Advisor mode: AI" in result.output
    assert "Selected provider: gemini" in result.output
    assert "Fallback used: No" in result.output


def test_ai_json_includes_router_metadata_and_hides_raw_response(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cli_module, "build_audit", lambda path: _fake_audit())
    monkeypatch.setattr(cli_module, "build_advisor_result", lambda *args, **kwargs: {"advisor_service_version": "v1", "profile_id": "student_portfolio", "advisor_report": _fake_advisor_report(), "prompt_bundle": {"system_prompt": "sys", "user_prompt": "usr"}})
    monkeypatch.setattr(cli_module, "route_llm_advisor_response", lambda prompt_bundle, fallback_response: {"router_version": "v1", "selected_provider_id": "gemini", "used_fallback": False, "provider_attempts": [{"provider_id": "gemini", "status": "ok"}], "advisor_response": _fake_advisor_report()["advisor_response"]})

    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "json", "--profile", "student_portfolio", "--ai"])

    assert result.exit_code == 0
    assert '"llm_router"' in result.output
    assert '"raw_response"' not in result.output
    assert 'abc123' not in result.output
    assert 'Authorization' not in result.output


def test_ai_fallback_path_still_succeeds(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cli_module, "build_audit", lambda path: _fake_audit())
    monkeypatch.setattr(cli_module, "build_advisor_result", lambda *args, **kwargs: {"advisor_service_version": "v1", "profile_id": "student_portfolio", "advisor_report": _fake_advisor_report(), "prompt_bundle": {"system_prompt": "sys", "user_prompt": "usr"}})
    monkeypatch.setattr(cli_module, "route_llm_advisor_response", lambda prompt_bundle, fallback_response: {"router_version": "v1", "selected_provider_id": "deterministic_fallback", "used_fallback": True, "provider_attempts": [{"provider_id": "gemini", "status": "error"}], "advisor_response": _fake_advisor_report()["advisor_response"]})

    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "summary", "--profile", "student_portfolio", "--ai"])

    assert result.exit_code == 0
    assert "Selected provider: deterministic_fallback" in result.output
    assert "Fallback used: Yes" in result.output
