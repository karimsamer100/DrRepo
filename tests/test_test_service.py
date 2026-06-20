import json
import pytest

from drrepo.analyzers import test_service
from drrepo.analyzers.models import ToolResult


def make_result(tool: str, status: str = "completed", **kwargs):
    return ToolResult(tool=tool, status=status, **kwargs)


def test_run_test_analyzers_returns_pytest_result(monkeypatch, tmp_path):
    monkeypatch.setattr(test_service, "run_pytest", lambda p: make_result("pytest", status="completed", summary={"passed": 3}))
    monkeypatch.setattr(test_service, "run_coverage", lambda p: make_result("coverage", status="completed", summary={"coverage_percent": 80.0}))
    res = test_service.run_test_analyzers(tmp_path)
    assert len(res) == 2
    assert res[0].tool == "pytest"
    assert res[0].status == "completed"
    assert res[1].tool == "coverage"
    assert res[1].status == "completed"


def test_run_test_analyzers_preserves_not_applicable(monkeypatch, tmp_path):
    monkeypatch.setattr(test_service, "run_pytest", lambda p: make_result("pytest", status="not_applicable"))
    monkeypatch.setattr(test_service, "run_coverage", lambda p: make_result("coverage", status="not_available"))
    res = test_service.run_test_analyzers(tmp_path)
    assert res[0].status == "not_applicable"
    assert res[1].status == "not_available"


def test_run_test_analyzers_catches_exceptions(monkeypatch, tmp_path):
    def boom(p):
        raise RuntimeError("boom")

    monkeypatch.setattr(test_service, "run_pytest", boom)
    # coverage should still be called and included
    monkeypatch.setattr(test_service, "run_coverage", lambda p: make_result("coverage", status="completed"))
    res = test_service.run_test_analyzers(tmp_path)
    assert len(res) == 2
    r = res[0]
    assert r.tool == "pytest"
    assert r.status == "failed_to_run"
    assert r.errors and len(r.errors) > 0
    # coverage result present
    assert res[1].tool == "coverage"
    assert res[1].status == "completed"


def test_test_analyzers_to_dict_serializable():
    results = [ToolResult(tool="pytest", status="completed"), ToolResult(tool="coverage", status="not_available")]
    d = test_service.test_analyzers_to_dict(results)
    json.dumps(d)


def test_run_test_analyzers_invalid_path():
    with pytest.raises(FileNotFoundError):
        test_service.run_test_analyzers("/this/path/does/not/exist")
