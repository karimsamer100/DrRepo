from pathlib import Path
import json
from typer.testing import CliRunner
import pytest

from drrepo.cli import app

runner = CliRunner()


MINIMAL_AUDIT = {
    "status": "ok",
    "path": "{repo}",
    "metadata": {"python_files": 1, "test_files": 1, "total_files": 2, "total_dirs": 1},
    "static_analysis": [],
    "test_analysis": [],
    "repository_analysis": [],
    "scoring": {
        "overall_score": 100,
        "overall": 100,
        "repository_health_score": 100,
        "portfolio_readiness_score": 100,
        "categories": {
            "code_quality": 100,
            "testing": 100,
            "security": 100,
            "maintainability": 100,
            "documentation": 100,
            "structure": 100,
        },
        "category_reasons": {},
    },
    "diagnosis": {
        "repository_health": {"label": "healthy", "score": 100, "summary": "Repository looks healthy based on available evidence."},
        "hard_flags": [],
        "limitations": [],
    },
    "remediation_suggestions": [],
    "remediation_summary": {"total": 0, "by_severity": {}},
}


def test_url_audit_calls_clone_and_build(monkeypatch, tmp_path):
    url = "https://github.com/Owner/Repo"
    called = {}

    def fake_create():
        called['create'] = True
        p = tmp_path / 'ws'
        p.mkdir()
        return p

    def fake_clone(u, ws):
        called['clone'] = u
        repo = ws / 'repo'
        repo.mkdir()
        return repo

    def fake_build(path):
        called['build'] = str(path)
        out = dict(MINIMAL_AUDIT)
        out['path'] = str(path)
        return out

    monkeypatch.setattr('drrepo.cli.create_temp_workspace', fake_create)
    monkeypatch.setattr('drrepo.cli.clone_public_github_repo', fake_clone)
    monkeypatch.setattr('drrepo.cli.cleanup_workspace', lambda p: called.update({'cleaned': True}))
    monkeypatch.setattr('drrepo.cli.build_audit', fake_build)

    result = runner.invoke(app, ['audit', url, '--format', 'json'])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data['status'] == 'ok'
    assert called.get('clone') == url
    assert 'source' in data and data['source']['type'] == 'github_url'


def test_url_audit_cleanup_on_success(monkeypatch, tmp_path):
    url = "https://github.com/Owner/Repo"
    called = {}

    monkeypatch.setattr('drrepo.cli.create_temp_workspace', lambda: tmp_path / 'ws')
    monkeypatch.setattr('drrepo.cli.clone_public_github_repo', lambda u, ws: tmp_path / 'ws' / 'repo')

    def fake_build(path):
        return dict(MINIMAL_AUDIT, path=str(path))

    monkeypatch.setattr('drrepo.cli.build_audit', fake_build)

    def fake_cleanup(p):
        called['cleanup'] = True

    monkeypatch.setattr('drrepo.cli.cleanup_workspace', fake_cleanup)

    result = runner.invoke(app, ['audit', url, '--format', 'json'])
    assert result.exit_code == 0
    assert called.get('cleanup') is True


def test_url_audit_cleanup_on_clone_failure(monkeypatch, tmp_path):
    url = "https://github.com/Owner/Repo"
    called = {}

    monkeypatch.setattr('drrepo.cli.create_temp_workspace', lambda: tmp_path / 'ws')

    def fake_clone(u, ws):
        raise RuntimeError('clone failed')

    monkeypatch.setattr('drrepo.cli.clone_public_github_repo', fake_clone)

    def fake_cleanup(p):
        called['cleanup'] = True

    monkeypatch.setattr('drrepo.cli.cleanup_workspace', fake_cleanup)

    result = runner.invoke(app, ['audit', url, '--format', 'json'])
    assert result.exit_code != 0
    assert 'clone failed' in result.output
    assert called.get('cleanup') is True


def test_invalid_github_url_fails():
    url = 'https://github.com/owner/repo/issues/1'
    result = runner.invoke(app, ['audit', url])
    assert result.exit_code != 0
    assert 'Invalid GitHub repository URL' in result.output


def test_local_path_does_not_clone(monkeypatch, tmp_path):
    # ensure clone is not called for local path
    monkeypatch.setattr('drrepo.cli.clone_public_github_repo', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('should not be called')))
    # use minimal local path audit
    def fake_build(path):
        return dict(MINIMAL_AUDIT, path=str(path))
    monkeypatch.setattr('drrepo.cli.build_audit', fake_build)

    result = runner.invoke(app, ['audit', str(tmp_path), '--format', 'json'])
    assert result.exit_code == 0


def test_url_supports_summary_format(monkeypatch, tmp_path):
    url = 'https://github.com/Owner/Repo'
    monkeypatch.setattr('drrepo.cli.create_temp_workspace', lambda: tmp_path / 'ws')
    monkeypatch.setattr('drrepo.cli.clone_public_github_repo', lambda u, ws: tmp_path / 'ws' / 'repo')
    monkeypatch.setattr('drrepo.cli.build_audit', lambda p: dict(MINIMAL_AUDIT, path=str(p)))
    monkeypatch.setattr('drrepo.cli.cleanup_workspace', lambda p: None)

    result = runner.invoke(app, ['audit', url, '--format', 'summary'])
    assert result.exit_code == 0
    assert 'DrRepo Audit Summary' in result.output


def test_url_supports_output_file(monkeypatch, tmp_path):
    url = 'https://github.com/Owner/Repo'
    monkeypatch.setattr('drrepo.cli.create_temp_workspace', lambda: tmp_path / 'ws')
    monkeypatch.setattr('drrepo.cli.clone_public_github_repo', lambda u, ws: tmp_path / 'ws' / 'repo')
    monkeypatch.setattr('drrepo.cli.build_audit', lambda p: dict(MINIMAL_AUDIT, path=str(p)))
    monkeypatch.setattr('drrepo.cli.cleanup_workspace', lambda p: None)

    out_file = tmp_path / 'audit.json'
    result = runner.invoke(app, ['audit', url, '--format', 'json', '--output', str(out_file)])
    assert result.exit_code == 0
    assert out_file.exists()
    d = json.loads(out_file.read_text(encoding='utf-8'))
    assert d.get('status') == 'ok'
