from pathlib import Path

from typer.testing import CliRunner

from drrepo.cli import app

runner = CliRunner()


def test_markdown_without_profile_does_not_include_advisor_section(tmp_path: Path):
    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "markdown"])
    assert result.exit_code == 0
    assert "Context-Aware Advisor" not in result.output


def test_markdown_with_profile_includes_advisor_section(tmp_path: Path):
    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "markdown", "--profile", "student_portfolio"])
    assert result.exit_code == 0
    assert "Context-Aware Advisor" in result.output
    assert "Student Portfolio" in result.output


def test_summary_with_profile_includes_advisor_summary_lines(tmp_path: Path):
    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "summary", "--profile", "student_portfolio"])
    assert result.exit_code == 0
    assert "Profile:" in result.output
    assert "Summary:" in result.output


def test_json_without_profile_does_not_include_advisor_report(tmp_path: Path):
    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "json"])
    assert result.exit_code == 0
    assert '"advisor_report"' not in result.output


def test_json_with_profile_includes_advisor_report(tmp_path: Path):
    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "json", "--profile", "student_portfolio"])
    assert result.exit_code == 0
    assert '"advisor_report"' in result.output


def test_invalid_profile_id_returns_clear_error(tmp_path: Path):
    result = runner.invoke(app, ["audit", str(tmp_path), "--format", "markdown", "--profile", "bad_profile"])
    assert result.exit_code != 0
    assert "unsupported profile" in result.output.lower() or "invalid profile" in result.output.lower()
