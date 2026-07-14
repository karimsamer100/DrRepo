import json
from pathlib import Path

from typer.testing import CliRunner

import drrepo.cli as cli_module
from drrepo.cli import app


runner = CliRunner()


def _audit(path: Path, **extra):
    return {
        "status": "ok",
        "path": str(path),
        "metadata": {},
        "static_analysis": [],
        "test_analysis": [],
        "repository_analysis": [],
        "scoring": {"overall_score": 100, "categories": {}},
        "diagnosis": {"repository_health": {"label": "healthy", "score": 100, "summary": "ok"}},
        "remediation_suggestions": [],
        "remediation_summary": {"total": 0, "by_severity": {}},
        **extra,
    }


def test_cli_local_defaults_to_deep_local(monkeypatch, tmp_path: Path):
    captured = {}

    def fake_build(path, **kwargs):
        captured.update(kwargs)
        return _audit(Path(path), analysis={"mode": kwargs["analysis_mode"]})

    monkeypatch.setattr(cli_module, "build_audit", fake_build)

    result = runner.invoke(app, ["audit", str(tmp_path)])

    assert result.exit_code == 0
    assert captured["source_type"] == "local_path"
    assert captured["analysis_mode"] == "deep_local"


def test_cli_accepts_quick_safe_for_local(monkeypatch, tmp_path: Path):
    captured = {}

    def fake_build(path, **kwargs):
        captured.update(kwargs)
        return _audit(Path(path), analysis={"mode": kwargs["analysis_mode"]})

    monkeypatch.setattr(cli_module, "build_audit", fake_build)

    result = runner.invoke(app, ["audit", str(tmp_path), "--analysis-mode", "quick_safe"])
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert captured["analysis_mode"] == "quick_safe"
    assert payload["analysis"]["mode"] == "quick_safe"


def test_cli_rejects_deep_local_for_github_without_cloning(monkeypatch):
    monkeypatch.setattr(
        cli_module,
        "clone_public_github_repo",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("should not clone")),
    )

    result = runner.invoke(
        app,
        ["audit", "https://github.com/owner/repo", "--analysis-mode", "deep_local"],
    )

    assert result.exit_code != 0
    assert "deep_local" in result.output


def test_cli_accepts_deep_isolated_when_docker_supported(monkeypatch, tmp_path: Path):
    from drrepo.execution.docker_runner import DockerCapability

    captured = {}

    def fake_build(path, **kwargs):
        captured.update(kwargs)
        return _audit(Path(path), analysis={"mode": kwargs["analysis_mode"]})

    monkeypatch.setattr(cli_module, "build_audit", fake_build)
    monkeypatch.setattr(
        cli_module,
        "check_docker_capability",
        lambda: DockerCapability(True, True, "27", "image", True, True, None),
    )

    result = runner.invoke(app, ["audit", str(tmp_path), "--analysis-mode", "deep-isolated", "--install-dependencies"])

    assert result.exit_code == 0
    assert captured["analysis_mode"] == "deep_isolated"
    assert captured["isolated_options"]["install_dependencies"] is True


def test_cli_rejects_deep_isolated_when_docker_unavailable(monkeypatch, tmp_path: Path):
    from drrepo.execution.docker_runner import DockerCapability

    monkeypatch.setattr(
        cli_module,
        "check_docker_capability",
        lambda: DockerCapability(False, False, None, "image", False, False, "Docker CLI is not installed."),
    )

    result = runner.invoke(app, ["audit", str(tmp_path), "--analysis-mode", "deep_isolated"])

    assert result.exit_code != 0
    assert "Docker CLI" in result.output
