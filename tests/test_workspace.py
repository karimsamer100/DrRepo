import subprocess
from pathlib import Path
import pytest

from drrepo.input.workspace import (
    create_temp_workspace,
    cleanup_workspace,
    clone_public_github_repo,
)
from drrepo.input.git import normalize_github_repo_url


def test_create_temp_workspace():
    p = create_temp_workspace()
    assert p.exists() and p.is_dir()
    # cleanup
    cleanup_workspace(p)


def test_cleanup_ignores_missing(tmp_path):
    p = tmp_path / "nope"
    # should not raise
    cleanup_workspace(p)


def test_cleanup_refuses_cwd():
    with pytest.raises(ValueError):
        cleanup_workspace(Path.cwd())


def test_clone_calls_git(monkeypatch, tmp_path):
    url = "https://github.com/owner/repo"
    norm = normalize_github_repo_url(url)
    called = {}

    class FakeProc:
        def __init__(self, rc=0):
            self.returncode = rc
            self.stdout = "ok"
            self.stderr = ""

    def fake_run(cmd, stdout, stderr, text, timeout):
        called['cmd'] = cmd
        return FakeProc(0)

    monkeypatch.setattr('subprocess.run', fake_run)
    ws = tmp_path / "ws"
    ws.mkdir()
    target = clone_public_github_repo(url, ws)
    assert target == ws / 'repo'
    assert called['cmd'][0:3] == ['git', 'clone', '--depth']
    assert norm in called['cmd']


def test_clone_returns_path_on_success(monkeypatch, tmp_path):
    class FakeProc:
        def __init__(self, rc=0):
            self.returncode = rc
            self.stdout = "ok"
            self.stderr = ""

    monkeypatch.setattr('subprocess.run', lambda *a, **k: FakeProc(0))
    ws = tmp_path / "ws2"
    ws.mkdir()
    target = clone_public_github_repo('https://github.com/owner/repo', ws)
    assert target == ws / 'repo'


def test_clone_raises_on_failure(monkeypatch, tmp_path):
    class FakeProc:
        def __init__(self, rc=1):
            self.returncode = rc
            self.stdout = ""
            self.stderr = "fatal"

    monkeypatch.setattr('subprocess.run', lambda *a, **k: FakeProc(1))
    ws = tmp_path / "ws3"
    ws.mkdir()
    with pytest.raises(RuntimeError):
        clone_public_github_repo('https://github.com/owner/repo', ws)


def test_clone_raises_if_target_exists(monkeypatch, tmp_path):
    monkeypatch.setattr('subprocess.run', lambda *a, **k: None)
    ws = tmp_path / "ws4"
    (ws / 'repo').mkdir(parents=True)
    with pytest.raises(FileExistsError):
        clone_public_github_repo('https://github.com/owner/repo', ws)


def test_clone_raises_if_git_missing(monkeypatch, tmp_path):
    def fake_run(*a, **k):
        raise FileNotFoundError()

    monkeypatch.setattr('subprocess.run', fake_run)
    ws = tmp_path / "ws5"
    ws.mkdir()
    with pytest.raises(RuntimeError):
        clone_public_github_repo('https://github.com/owner/repo', ws)
