import json
import pytest
from types import SimpleNamespace

from drrepo.analyzers import service
from drrepo.analyzers.models import ToolResult


def make_result(tool: str, status: str = "completed"):
    return ToolResult(tool=tool, status=status)


def test_run_static_analyzers_order(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "run_ruff", lambda p: make_result("ruff"))
    monkeypatch.setattr(service, "run_bandit", lambda p: make_result("bandit"))
    monkeypatch.setattr(service, "run_radon", lambda p: make_result("radon"))

    res = service.run_static_analyzers(tmp_path)
    assert [r.tool for r in res] == ["ruff", "bandit", "radon"]


def test_run_static_analyzers_continue_on_not_available(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "run_ruff", lambda p: make_result("ruff", status="not_available"))
    monkeypatch.setattr(service, "run_bandit", lambda p: make_result("bandit"))
    monkeypatch.setattr(service, "run_radon", lambda p: make_result("radon"))

    res = service.run_static_analyzers(tmp_path)
    assert len(res) == 3
    assert res[0].status == "not_available"


def test_run_static_analyzers_catches_exceptions(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "run_ruff", lambda p: make_result("ruff"))

    def boom(p):
        raise RuntimeError("boom")

    monkeypatch.setattr(service, "run_bandit", boom)
    monkeypatch.setattr(service, "run_radon", lambda p: make_result("radon"))

    res = service.run_static_analyzers(tmp_path)
    assert len(res) == 3
    b = res[1]
    assert b.tool == "bandit"
    assert b.status == "failed_to_run"
    assert b.errors and len(b.errors) > 0


def test_static_analyzers_to_dict_serializable():
    results = [ToolResult(tool="ruff", status="completed"), ToolResult(tool="bandit", status="not_available")]
    d = service.static_analyzers_to_dict(results)
    # Should be JSON serializable
    json.dumps(d)


def test_run_static_analyzers_invalid_path():
    with pytest.raises(FileNotFoundError):
        service.run_static_analyzers("/this/path/does/not/exist")
