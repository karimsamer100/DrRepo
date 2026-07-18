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


def _fake_ai_package(
    *,
    source: str = "ai",
    provider: str = "gemini",
    used_fallback: bool = False,
    grounding_valid: bool = True,
) -> dict[str, object]:
    return {
        "advisor_service_version": "v1",
        "profile_id": "student_portfolio",
        "advisor_report": _fake_advisor_report(),
        "ai": {
            "requested": True,
            "status": "ok" if source == "ai" else "fallback",
            "source": source,
            "provider": provider,
            "model": "gemini-2.5-flash" if provider == "gemini" else "deterministic-advisor",
            "advisor_response": _fake_advisor_report()["advisor_response"],
            "grounding_result": {
                "valid": grounding_valid,
                "checked_claims": 3,
                "validated_references": 3,
                "violations": [],
            },
            "fallback_reason": None if not used_fallback else "Provider unavailable; using deterministic guidance.",
            "limitations": ["No coverage data."],
            "duration_ms": 120,
            "router_result": {
                "selected_provider_id": provider,
                "used_fallback": used_fallback,
                "provider_attempts": [{"provider_id": provider, "status": "ok"}],
            },
        },
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

    def fake_build_advisor_for_audit(audit, profile_id="student_portfolio", ai=False, **kwargs):
        captured["profile_id"] = profile_id
        captured["ai"] = ai
        return _fake_ai_package()

    monkeypatch.setattr(cli_module, "build_advisor_for_audit", fake_build_advisor_for_audit)

    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "summary", "--ai"])

    assert result.exit_code == 0
    assert captured["profile_id"] == "student_portfolio"
    assert captured["ai"] is True
    assert "Advisor mode: AI" in result.output
    assert "Selected provider: gemini" in result.output


def test_ai_markdown_includes_ai_advisor_guidance_and_provider_metadata(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cli_module, "build_audit", lambda path: _fake_audit())
    monkeypatch.setattr(cli_module, "build_advisor_for_audit", lambda *args, **kwargs: _fake_ai_package())

    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "markdown", "--profile", "student_portfolio", "--ai"])

    assert result.exit_code == 0
    assert "## AI Advisor Guidance" in result.output
    assert "**Provider**: gemini" in result.output
    assert "**Grounding**: valid" in result.output


def test_ai_summary_includes_selected_provider_metadata(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cli_module, "build_audit", lambda path: _fake_audit())
    monkeypatch.setattr(cli_module, "build_advisor_for_audit", lambda *args, **kwargs: _fake_ai_package())

    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "summary", "--profile", "student_portfolio", "--ai"])

    assert result.exit_code == 0
    assert "Advisor mode: AI" in result.output
    assert "Selected provider: gemini" in result.output
    assert "Fallback used: No" in result.output


def test_ai_json_includes_router_metadata_and_hides_raw_response(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cli_module, "build_audit", lambda path: _fake_audit())
    monkeypatch.setattr(cli_module, "build_advisor_for_audit", lambda *args, **kwargs: _fake_ai_package())

    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "json", "--profile", "student_portfolio", "--ai"])

    assert result.exit_code == 0
    assert '"llm_router"' in result.output
    assert '"ai_advisor"' in result.output
    assert '"raw_response"' not in result.output
    assert 'abc123' not in result.output
    assert 'Authorization' not in result.output


def test_ai_fallback_path_still_succeeds(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cli_module, "build_audit", lambda path: _fake_audit())
    monkeypatch.setattr(
        cli_module,
        "build_advisor_for_audit",
        lambda *args, **kwargs: _fake_ai_package(source="deterministic", provider="deterministic_fallback", used_fallback=True),
    )

    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "summary", "--profile", "student_portfolio", "--ai"])

    assert result.exit_code == 0
    assert "Selected provider: deterministic_fallback" in result.output
    assert "Fallback used: Yes" in result.output
    assert "Advisor mode: DETERMINISTIC" in result.output


def test_ai_grounding_rejected_shows_fallback(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cli_module, "build_audit", lambda path: _fake_audit())
    package = _fake_ai_package()
    package["ai"]["status"] = "grounding_rejected"  # type: ignore[index]
    package["ai"]["source"] = "deterministic"  # type: ignore[index]
    package["ai"]["grounding_result"] = {  # type: ignore[index]
        "valid": False,
        "checked_claims": 3,
        "validated_references": 2,
        "violations": ["unknown evidence reference: tests/"],
    }
    package["ai"]["fallback_reason"] = "AI response contradicted the audit evidence; using deterministic guidance."  # type: ignore[index]
    monkeypatch.setattr(cli_module, "build_advisor_for_audit", lambda *args, **kwargs: package)

    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "summary", "--profile", "student_portfolio", "--ai"])

    assert result.exit_code == 0
    assert "Grounding: rejected" in result.output
    assert "Fallback used: Yes" in result.output
