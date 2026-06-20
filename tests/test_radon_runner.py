import json
import subprocess

from drrepo.analyzers.radon_runner import parse_radon_cc_json, run_radon
from drrepo.analyzers.models import ToolFinding


def test_parse_radon_empty_output():
    raw = "{}"
    res = parse_radon_cc_json(raw)
    assert res.status == "completed"
    assert res.summary.get("block_count") == 0
    assert res.summary.get("max_complexity") == 0
    assert res.summary.get("average_complexity") == 0
    assert res.findings == []


def test_parse_radon_one_block():
    blk = {
        "type": "function",
        "rank": "A",
        "name": "main",
        "lineno": 1,
        "col_offset": 0,
        "complexity": 2,
    }
    raw = json.dumps({"app.py": [blk]})
    res = parse_radon_cc_json(raw)
    assert res.status == "completed"
    assert res.summary.get("block_count") == 1
    assert res.summary.get("max_complexity") == 2
    assert res.summary.get("average_complexity") == 2
    assert len(res.findings) == 1
    f = res.findings[0]
    assert isinstance(f, ToolFinding)
    assert f.tool == "radon"
    assert f.code == "RADON-CC"
    assert f.file_path == "app.py"
    assert f.line == 1
    assert f.column == 1
    assert f.severity == "A"


def test_parse_radon_multiple_blocks():
    b1 = {"type": "function", "rank": "A", "name": "f1", "lineno": 1, "col_offset": 0, "complexity": 2}
    b2 = {"type": "function", "rank": "C", "name": "f2", "lineno": 10, "col_offset": 2, "complexity": 6}
    raw = json.dumps({"a.py": [b1], "b.py": [b2]})
    res = parse_radon_cc_json(raw)
    assert res.status == "completed"
    assert res.summary.get("block_count") == 2
    assert res.summary.get("max_complexity") == 6
    assert res.summary.get("average_complexity") == 4


def test_parse_radon_average_float():
    b1 = {"type": "function", "rank": "A", "name": "f1", "lineno": 1, "col_offset": 0, "complexity": 2}
    b2 = {"type": "function", "rank": "B", "name": "f2", "lineno": 5, "col_offset": 1, "complexity": 5}
    raw = json.dumps({"a.py": [b1], "b.py": [b2]})
    res = parse_radon_cc_json(raw)
    assert res.status == "completed"
    assert res.summary.get("block_count") == 2
    assert res.summary.get("max_complexity") == 5
    assert res.summary.get("average_complexity") == 3.5


def test_parse_radon_malformed_json():
    raw = "not json"
    res = parse_radon_cc_json(raw)
    assert res.status == "failed_to_run"
    assert res.errors and len(res.errors) > 0


def test_parse_radon_not_dict():
    raw = "[]"
    res = parse_radon_cc_json(raw)
    assert res.status == "failed_to_run"
    assert res.errors and len(res.errors) > 0


def test_parse_radon_file_not_list():
    raw = json.dumps({"app.py": {}})
    res = parse_radon_cc_json(raw)
    assert res.status == "failed_to_run"
    assert res.errors and len(res.errors) > 0


def test_run_radon_stdout_empty(monkeypatch, tmp_path):
    class P:
        stdout = "{}"
        stderr = ""
        returncode = 0

    def fake_run(*args, **kwargs):
        return P()

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = run_radon(tmp_path)
    assert res.status == "completed"
    assert res.summary.get("block_count") == 0


def test_run_radon_not_installed(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("no radon")

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = run_radon(tmp_path)
    assert res.status == "not_available"


def test_run_radon_timeout(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="radon", timeout=30)

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = run_radon(tmp_path)
    assert res.status == "failed_to_run"
    assert any("timed out" in e.lower() or "timeout" in e.lower() for e in (res.errors or []))


def test_run_radon_missing_module(monkeypatch, tmp_path):
    class P:
        stdout = ""
        stderr = "No module named radon"
        returncode = 1

    def fake_run(*args, **kwargs):
        return P()

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = run_radon(tmp_path)
    assert res.status == "not_available"
    assert res.errors and len(res.errors) > 0


def test_run_radon_invalid_stdout_and_stderr(monkeypatch, tmp_path):
    class P:
        stdout = "not json"
        stderr = "boom"
        returncode = 2

    def fake_run(*args, **kwargs):
        return P()

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = run_radon(tmp_path)
    assert res.status == "failed_to_run"
    assert res.errors and len(res.errors) > 0
