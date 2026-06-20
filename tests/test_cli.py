from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from drrepo.cli import app


runner = CliRunner()


def test_help_shows_audit():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "audit" in result.output


def test_audit_placeholder_ok(tmp_path: Path):
    result = runner.invoke(app, ["audit", str(tmp_path)])
    assert result.exit_code == 0
    assert '"status": "ok"' in result.output


def test_audit_missing_path():
    result = runner.invoke(app, ["audit", "no/such/path"]) 
    assert result.exit_code != 0
