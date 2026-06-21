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
        "overall": 100,
        "overall_score": 100,
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


def test_github_url_audit_json(monkeypatch, tmp_path):
    url = 'https://github.com/Owner/Repo'
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

    def fake_cleanup(p):
        called['cleanup'] = str(p)

    monkeypatch.setattr('drrepo.cli.create_temp_workspace', fake_create)
    monkeypatch.setattr('drrepo.cli.clone_public_github_repo', fake_clone)
    monkeypatch.setattr('drrepo.cli.build_audit', fake_build)
    monkeypatch.setattr('drrepo.cli.cleanup_workspace', fake_cleanup)

    result = runner.invoke(app, ['audit', url, '--format', 'json'])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data['status'] == 'ok'
    assert 'source' in data and data['source']['type'] == 'github_url' and data['source']['value'] == url
    assert called.get('create')
    assert called.get('clone') == url
    assert called.get('build')
    assert called.get('cleanup')


def test_github_url_audit_markdown(monkeypatch, tmp_path):
    url = 'https://github.com/Owner/Repo'
    monkeypatch.setattr('drrepo.cli.create_temp_workspace', lambda: tmp_path / 'ws')
    monkeypatch.setattr('drrepo.cli.clone_public_github_repo', lambda u, ws: tmp_path / 'ws' / 'repo')
    monkeypatch.setattr('drrepo.cli.build_audit', lambda p: dict(MINIMAL_AUDIT, path=str(p)))
    monkeypatch.setattr('drrepo.cli.cleanup_workspace', lambda p: None)

    result = runner.invoke(app, ['audit', url, '--format', 'markdown'])
    assert result.exit_code == 0
    out = result.output
    assert '# DrRepo Audit Report' in out
    assert '## Diagnosis' in out
    assert '## Prioritized Action Plan' in out


def test_github_url_audit_summary(monkeypatch, tmp_path):
    url = 'https://github.com/Owner/Repo'
    monkeypatch.setattr('drrepo.cli.create_temp_workspace', lambda: tmp_path / 'ws')
    monkeypatch.setattr('drrepo.cli.clone_public_github_repo', lambda u, ws: tmp_path / 'ws' / 'repo')
    monkeypatch.setattr('drrepo.cli.build_audit', lambda p: dict(MINIMAL_AUDIT, path=str(p)))
    monkeypatch.setattr('drrepo.cli.cleanup_workspace', lambda p: None)

    result = runner.invoke(app, ['audit', url, '--format', 'summary'])
    assert result.exit_code == 0
    out = result.output
    assert 'DrRepo Audit Summary' in out
    assert 'Overall score' in out
    assert 'Diagnosis' in out
    assert 'Suggestions:' in out


def test_github_url_supports_output_files(monkeypatch, tmp_path):
    url = 'https://github.com/Owner/Repo'
    monkeypatch.setattr('drrepo.cli.create_temp_workspace', lambda: tmp_path / 'ws')
    monkeypatch.setattr('drrepo.cli.clone_public_github_repo', lambda u, ws: tmp_path / 'ws' / 'repo')
    monkeypatch.setattr('drrepo.cli.build_audit', lambda p: dict(MINIMAL_AUDIT, path=str(p)))
    monkeypatch.setattr('drrepo.cli.cleanup_workspace', lambda p: None)

    # json
    out_json = tmp_path / 'audit.json'
    r = runner.invoke(app, ['audit', url, '--format', 'json', '--output', str(out_json)])
    assert r.exit_code == 0
    assert out_json.exists()
    json.loads(out_json.read_text(encoding='utf-8'))
    assert 'Wrote audit report to' in r.output

    # markdown
    out_md = tmp_path / 'audit.md'
    r = runner.invoke(app, ['audit', url, '--format', 'markdown', '--output', str(out_md)])
    assert r.exit_code == 0
    assert out_md.exists()
    assert '# DrRepo Audit Report' in out_md.read_text(encoding='utf-8')
    assert 'Wrote audit report to' in r.output

    # summary
    out_txt = tmp_path / 'audit.txt'
    r = runner.invoke(app, ['audit', url, '--format', 'summary', '--output', str(out_txt)])
    assert r.exit_code == 0
    assert out_txt.exists()
    assert 'DrRepo Audit Summary' in out_txt.read_text(encoding='utf-8')
    assert 'Wrote audit report to' in r.output


def test_cleanup_runs_after_success(monkeypatch, tmp_path):
    url = 'https://github.com/Owner/Repo'
    calls = {}
    monkeypatch.setattr('drrepo.cli.create_temp_workspace', lambda: tmp_path / 'ws')
    monkeypatch.setattr('drrepo.cli.clone_public_github_repo', lambda u, ws: tmp_path / 'ws' / 'repo')
    monkeypatch.setattr('drrepo.cli.build_audit', lambda p: dict(MINIMAL_AUDIT, path=str(p)))

    def fake_cleanup(p):
        calls['cleanup'] = str(p)

    monkeypatch.setattr('drrepo.cli.cleanup_workspace', fake_cleanup)

    r = runner.invoke(app, ['audit', url, '--format', 'json'])
    assert r.exit_code == 0
    assert 'cleanup' in calls


def test_cleanup_runs_if_build_fails(monkeypatch, tmp_path):
    url = 'https://github.com/Owner/Repo'
    calls = {}
    monkeypatch.setattr('drrepo.cli.create_temp_workspace', lambda: tmp_path / 'ws')
    monkeypatch.setattr('drrepo.cli.clone_public_github_repo', lambda u, ws: tmp_path / 'ws' / 'repo')

    def boom(path):
        raise RuntimeError('audit failed')

    monkeypatch.setattr('drrepo.cli.build_audit', boom)

    def fake_cleanup(p):
        calls['cleanup'] = True

    monkeypatch.setattr('drrepo.cli.cleanup_workspace', fake_cleanup)

    r = runner.invoke(app, ['audit', url, '--format', 'json'])
    assert r.exit_code != 0
    assert calls.get('cleanup') is True


def test_cleanup_runs_if_clone_fails(monkeypatch, tmp_path):
    url = 'https://github.com/Owner/Repo'
    calls = {}
    monkeypatch.setattr('drrepo.cli.create_temp_workspace', lambda: tmp_path / 'ws')

    def boom(u, ws):
        raise RuntimeError('clone failed')

    monkeypatch.setattr('drrepo.cli.clone_public_github_repo', boom)

    def fake_cleanup(p):
        calls['cleanup'] = True

    monkeypatch.setattr('drrepo.cli.cleanup_workspace', fake_cleanup)

    r = runner.invoke(app, ['audit', url, '--format', 'json'])
    assert r.exit_code != 0
    assert calls.get('cleanup') is True


def test_invalid_issue_url_fails_before_workspace(monkeypatch):
    url = 'https://github.com/owner/repo/issues/1'
    called = {}
    monkeypatch.setattr('drrepo.cli.create_temp_workspace', lambda: called.update({'created': True}))
    r = runner.invoke(app, ['audit', url])
    assert r.exit_code != 0
    assert 'Invalid GitHub repository URL' in r.output
    assert called == {}


def test_invalid_owner_only_fails_before_workspace(monkeypatch):
    url = 'https://github.com/owner'
    called = {}
    monkeypatch.setattr('drrepo.cli.create_temp_workspace', lambda: called.update({'created': True}))
    r = runner.invoke(app, ['audit', url])
    assert r.exit_code != 0
    assert 'Invalid GitHub repository URL' in r.output
    assert called == {}


def test_local_path_does_not_call_clone(monkeypatch, tmp_path):
    # make clone raise AssertionError if called
    def bad_clone(*a, **k):
        raise AssertionError('clone should not be called for local paths')

    monkeypatch.setattr('drrepo.cli.clone_public_github_repo', bad_clone)
    monkeypatch.setattr('drrepo.cli.build_audit', lambda p: dict(MINIMAL_AUDIT, path=str(p)))

    r = runner.invoke(app, ['audit', str(tmp_path), '--format', 'json'])
    assert r.exit_code == 0


def test_clone_failure_message_helpful(monkeypatch, tmp_path):
    url = 'https://github.com/Owner/Repo'
    monkeypatch.setattr('drrepo.cli.create_temp_workspace', lambda: tmp_path / 'ws')

    def boom(u, ws):
        raise RuntimeError('authentication failed or repository not found')

    monkeypatch.setattr('drrepo.cli.clone_public_github_repo', boom)
    monkeypatch.setattr('drrepo.cli.cleanup_workspace', lambda p: None)

    r = runner.invoke(app, ['audit', url])
    assert r.exit_code != 0
    # should include the concise reason
    assert 'authentication failed or repository not found' in r.output


def test_local_json_backward_compatible(monkeypatch, tmp_path):
    # local audit shouldn't require source metadata
    monkeypatch.setattr('drrepo.cli.build_audit', lambda p: dict(MINIMAL_AUDIT, path=str(p)))
    r = runner.invoke(app, ['audit', str(tmp_path), '--format', 'json'])
    assert r.exit_code == 0
    data = json.loads(r.output)
    assert 'source' not in data
