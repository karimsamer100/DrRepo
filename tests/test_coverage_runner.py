import json
import subprocess

from drrepo.analyzers.coverage_runner import parse_coverage_json, run_coverage


def test_parse_coverage_valid():
    raw = json.dumps({"totals": {"covered_lines": 10, "num_statements": 20, "percent_covered": 50.0, "missing_lines": 10}})
    res = parse_coverage_json(raw)
    assert res.status == "completed"
    assert res.summary["coverage_percent"] == 50.0
    assert res.summary["covered_lines"] == 10
    assert res.summary["num_statements"] == 20
    assert res.summary["missing_lines"] == 10


def test_parse_coverage_malformed():
    res = parse_coverage_json("not json")
    assert res.status == "failed_to_run"
    assert res.errors and len(res.errors) > 0


def test_parse_coverage_missing_totals():
    res = parse_coverage_json("{}")
    assert res.status == "failed_to_run"
    assert res.errors and len(res.errors) > 0


def test_parse_coverage_empty():
    res = parse_coverage_json("")
    assert res.status == "failed_to_run"
    assert res.errors and len(res.errors) > 0


def test_run_coverage_success(monkeypatch, tmp_path):
    # First call: coverage run
    class R1:
        stdout = "."
        stderr = ""
        returncode = 0

    # Second call: coverage json
    class R2:
        stdout = json.dumps({"totals": {"covered_lines": 10, "num_statements": 20, "percent_covered": 50.0, "missing_lines": 10}})
        stderr = ""
        returncode = 0

    calls = {"i": 0}

    def fake_run(*args, **kwargs):
        if calls["i"] == 0:
            calls["i"] += 1
            return R1()
        # second call: coverage json -o <tmpfile>
        cmd = args[0]
        try:
            out_idx = cmd.index("-o")
            out_path = cmd[out_idx + 1]
        except Exception:
            out_path = cmd[-1]

        # write expected JSON into the temp file path so run_coverage can read it
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(R2.stdout)

        return R2()

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = run_coverage(tmp_path)
    assert res.status == "completed"
    assert res.summary["coverage_percent"] == 50.0


def test_run_coverage_not_installed(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("no coverage")

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = run_coverage(tmp_path)
    assert res.status == "not_available"


def test_run_coverage_timeout(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="coverage", timeout=60)

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = run_coverage(tmp_path)
    assert res.status == "failed_to_run"
    assert any("timed out" in e.lower() or "timeout" in e.lower() for e in (res.errors or []))


def test_run_coverage_missing_module_in_run(monkeypatch, tmp_path):
    class R:
        stdout = ""
        stderr = "No module named coverage"
        returncode = 1

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: R())
    res = run_coverage(tmp_path)
    assert res.status == "not_available"


def test_run_coverage_json_invalid(monkeypatch, tmp_path):
    # coverage run succeeds, coverage json returns invalid
    class R1:
        stdout = "."
        stderr = ""
        returncode = 0

    class R2:
        stdout = "not json"
        stderr = "boom"
        returncode = 2

    calls = {"i": 0}

    def fake_run(*args, **kwargs):
        if calls["i"] == 0:
            calls["i"] += 1
            return R1()
        # write invalid JSON into the temp file path
        cmd = args[0]
        try:
            out_idx = cmd.index("-o")
            out_path = cmd[out_idx + 1]
        except Exception:
            out_path = cmd[-1]

        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(R2.stdout)

        return R2()

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = run_coverage(tmp_path)
    assert res.status == "failed_to_run"
    assert res.errors and len(res.errors) > 0
