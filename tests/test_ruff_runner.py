import json
import subprocess
from pathlib import Path

import pytest

from drrepo.analyzers.ruff_runner import parse_ruff_json, run_ruff
from drrepo.analyzers.models import ToolFinding


def test_parse_ruff_empty_list():
    raw = "[]"
    res = parse_ruff_json(raw)
    assert res.status == "completed"
    assert res.summary.get("issue_count") == 0
    assert res.findings == []


def test_parse_ruff_one_issue():
    issue = {
        "code": "F401",
        "message": "`os` imported but unused",
        "filename": "app.py",
        "location": {"row": 1, "column": 8},
    }
    raw = json.dumps([issue])
    res = parse_ruff_json(raw)
    assert res.status == "completed"
    assert res.summary.get("issue_count") == 1
    assert len(res.findings) == 1
    f = res.findings[0]
    assert isinstance(f, ToolFinding)
    assert f.tool == "ruff"
    assert f.code == "F401"
    assert f.file_path == "app.py"
    assert f.line == 1
    assert f.column == 8


def test_parse_ruff_malformed_json():
    raw = "not json"
    res = parse_ruff_json(raw)
    assert res.status == "failed_to_run"
    assert res.errors and len(res.errors) > 0


def test_parse_ruff_not_list():
    raw = "{}"
    res = parse_ruff_json(raw)
    assert res.status == "failed_to_run"
    assert res.errors and len(res.errors) > 0


def test_run_ruff_stdout_empty(monkeypatch, tmp_path):
    # subprocess.run returns a completed process with stdout=[]
    class P:
        stdout = "[]"
        stderr = ""
        returncode = 0

    def fake_run(*args, **kwargs):
        return P()

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = run_ruff(tmp_path)
    assert res.status == "completed"
    assert res.summary.get("issue_count") == 0


def test_run_ruff_not_installed(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("no ruff")

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = run_ruff(tmp_path)
    assert res.status == "not_available"


def test_run_ruff_timeout(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="ruff", timeout=30)

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = run_ruff(tmp_path)
    assert res.status == "failed_to_run"
    assert any("timed out" in e.lower() or "timeout" in e.lower() for e in (res.errors or []))


def test_run_ruff_invalid_stdout_and_stderr(monkeypatch, tmp_path):
    class P:
        stdout = "not json"
        stderr = "boom"
        returncode = 2

    def fake_run(*args, **kwargs):
        return P()

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = run_ruff(tmp_path)
    assert res.status == "failed_to_run"
    assert res.errors and len(res.errors) > 0


def test_run_ruff_missing_ruff_module(monkeypatch, tmp_path):
    class P:
        stdout = ""
        stderr = "No module named ruff"
        returncode = 1

    def fake_run(*args, **kwargs):
        return P()

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = run_ruff(tmp_path)
    assert res.status == "not_available"
    assert res.errors and len(res.errors) > 0
