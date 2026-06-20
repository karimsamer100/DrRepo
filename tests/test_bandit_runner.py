import json
import subprocess

from drrepo.analyzers.bandit_runner import parse_bandit_json, run_bandit
from drrepo.analyzers.models import ToolFinding


def test_parse_bandit_empty_results():
    raw = json.dumps({"results": []})
    res = parse_bandit_json(raw)
    assert res.status == "completed"
    assert res.summary.get("issue_count") == 0
    assert res.findings == []


def test_parse_bandit_one_issue():
    issue = {
        "filename": "app.py",
        "line_number": 10,
        "issue_text": "Use of assert detected",
        "issue_severity": "LOW",
        "issue_confidence": "HIGH",
        "test_id": "B101",
    }
    raw = json.dumps({"results": [issue]})
    res = parse_bandit_json(raw)
    assert res.status == "completed"
    assert res.summary.get("issue_count") == 1
    assert len(res.findings) == 1
    f = res.findings[0]
    assert isinstance(f, ToolFinding)
    assert f.tool == "bandit"
    assert f.code == "B101"
    assert f.file_path == "app.py"
    assert f.line == 10
    assert f.severity == "LOW"


def test_parse_bandit_malformed_json():
    raw = "not json"
    res = parse_bandit_json(raw)
    assert res.status == "failed_to_run"
    assert res.errors and len(res.errors) > 0


def test_parse_bandit_missing_results():
    raw = json.dumps({})
    res = parse_bandit_json(raw)
    assert res.status == "failed_to_run"
    assert res.errors and len(res.errors) > 0


def test_run_bandit_stdout_empty(monkeypatch, tmp_path):
    class P:
        stdout = json.dumps({"results": []})
        stderr = ""
        returncode = 0

    def fake_run(*args, **kwargs):
        return P()

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = run_bandit(tmp_path)
    assert res.status == "completed"
    assert res.summary.get("issue_count") == 0


def test_run_bandit_not_installed(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("no bandit")

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = run_bandit(tmp_path)
    assert res.status == "not_available"


def test_run_bandit_timeout(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="bandit", timeout=30)

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = run_bandit(tmp_path)
    assert res.status == "failed_to_run"
    assert any("timed out" in e.lower() or "timeout" in e.lower() for e in (res.errors or []))


def test_run_bandit_missing_module(monkeypatch, tmp_path):
    class P:
        stdout = ""
        stderr = "No module named bandit"
        returncode = 1

    def fake_run(*args, **kwargs):
        return P()

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = run_bandit(tmp_path)
    assert res.status == "not_available"
    assert res.errors and len(res.errors) > 0


def test_run_bandit_invalid_stdout_and_stderr(monkeypatch, tmp_path):
    class P:
        stdout = "not json"
        stderr = "boom"
        returncode = 2

    def fake_run(*args, **kwargs):
        return P()

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = run_bandit(tmp_path)
    assert res.status == "failed_to_run"
    assert res.errors and len(res.errors) > 0
