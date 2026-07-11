import subprocess

from drrepo.analyzers.pytest_runner import parse_pytest_output, run_pytest
from drrepo.analyzers.models import ToolFinding


def test_parse_pytest_passed():
    out = "3 passed in 0.12s"
    res = parse_pytest_output(out, "", 0)
    assert res.status == "completed"
    assert res.summary["outcome"] == "passed"
    assert res.summary["passed"] == 3
    assert res.summary["failed"] == 0
    assert res.summary["errors"] == 0
    assert res.findings == []


def test_parse_pytest_failed_and_passed():
    out = "2 failed, 5 passed in 1.20s"
    res = parse_pytest_output(out, "", 0)
    assert res.status == "completed"
    assert res.summary["outcome"] == "failed_tests"
    assert res.summary["failed"] == 2
    assert res.summary["passed"] == 5
    assert any(f.code == "PYTEST-FAILED" for f in res.findings)


def test_parse_pytest_error_and_passed():
    out = "1 error, 2 passed in 0.33s"
    res = parse_pytest_output(out, "", 0)
    assert res.status == "completed"
    assert res.summary["outcome"] == "collection_error"
    assert res.summary["errors"] == 1
    assert any("collection/runtime" in f.message for f in res.findings)
    assert any(f.code == "PYTEST-ERROR" for f in res.findings)


def test_parse_pytest_skipped_and_passed():
    out = "1 skipped, 4 passed in 0.50s"
    res = parse_pytest_output(out, "", 0)
    assert res.summary["skipped"] == 1
    assert res.summary["passed"] == 4


def test_parse_pytest_no_tests_ran():
    out = "no tests ran in 0.01s"
    res = parse_pytest_output(out, "", 0)
    assert res.status == "not_applicable"
    assert res.summary["outcome"] == "no_tests"
    assert res.summary["passed"] == 0
    assert res.summary["failed"] == 0
    assert res.summary["errors"] == 0


def test_parse_pytest_no_tests_ran_from_stderr():
    res = parse_pytest_output("", "no tests ran in 0.01s", 5)
    assert res.status == "not_applicable"
    assert res.summary["outcome"] == "no_tests"


def test_parse_pytest_unparsable_with_error():
    out = "garbage"
    res = parse_pytest_output(out, "boom", 1)
    assert res.status == "failed_to_run"
    assert res.summary["outcome"] == "env_error"
    assert res.errors == ["Pytest could not run: boom"]
    assert res.errors and len(res.errors) > 0


def test_parse_pytest_extracts_import_reason():
    stdout = "ERROR collecting tests/test_app.py"
    stderr = "ModuleNotFoundError: No module named 'app'"
    res = parse_pytest_output(stdout, stderr, 1)
    assert res.status == "failed_to_run"
    assert res.summary["outcome"] == "env_error"
    assert "ModuleNotFoundError: No module named 'app'" in res.errors[0]


def test_run_pytest_success(monkeypatch, tmp_path):
    class P:
        stdout = "3 passed in 0.12s"
        stderr = ""
        returncode = 0

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: P())
    res = run_pytest(tmp_path)
    assert res.status == "completed"
    assert res.summary["passed"] == 3


def test_run_pytest_not_installed(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("no pytest")

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = run_pytest(tmp_path)
    assert res.status == "not_available"
    assert res.summary["outcome"] == "pytest_unavailable"


def test_run_pytest_timeout(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="pytest", timeout=60)

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = run_pytest(tmp_path)
    assert res.status == "failed_to_run"
    assert res.summary["outcome"] == "timeout"
    assert any("timed out" in e.lower() or "timeout" in e.lower() for e in (res.errors or []))


def test_run_pytest_missing_module(monkeypatch, tmp_path):
    class P:
        stdout = ""
        stderr = "No module named pytest"
        returncode = 1

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: P())
    res = run_pytest(tmp_path)
    assert res.status == "not_available"
    assert res.errors == ["Pytest was not available in this environment."]
