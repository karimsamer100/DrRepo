import json

from drrepo.analyzers import repository_service
from drrepo.analyzers.models import ToolResult


def make_result(tool: str, status: str = "completed", **kwargs):
    return ToolResult(tool=tool, status=status, **kwargs)


def test_run_repository_analyzers_order(monkeypatch, tmp_path):
    monkeypatch.setattr(repository_service, "audit_readme", lambda p: make_result("readme", status="completed"))
    monkeypatch.setattr(repository_service, "audit_structure", lambda p: make_result("structure", status="completed"))
    res = repository_service.run_repository_analyzers(tmp_path)
    assert len(res) == 2
    assert [r.tool for r in res] == ["readme", "structure"]


def test_preserves_not_applicable(monkeypatch, tmp_path):
    monkeypatch.setattr(repository_service, "audit_readme", lambda p: make_result("readme", status="not_applicable"))
    monkeypatch.setattr(repository_service, "audit_structure", lambda p: make_result("structure", status="completed"))
    res = repository_service.run_repository_analyzers(tmp_path)
    assert res[0].status == "not_applicable"
    assert res[1].status == "completed"


def test_catches_exceptions(monkeypatch, tmp_path):
    monkeypatch.setattr(repository_service, "audit_readme", lambda p: make_result("readme", status="completed"))

    def boom(p):
        raise RuntimeError("boom")

    monkeypatch.setattr(repository_service, "audit_structure", boom)
    res = repository_service.run_repository_analyzers(tmp_path)
    assert len(res) == 2
    assert res[0].tool == "readme"
    assert res[1].tool == "structure"
    assert res[1].status == "failed_to_run"
    assert res[1].errors and len(res[1].errors) > 0


def test_repository_analyzers_to_dict_serializable():
    results = [ToolResult(tool="readme", status="completed"), ToolResult(tool="structure", status="not_available")]
    d = repository_service.repository_analyzers_to_dict(results)
    json.dumps(d)


def test_invalid_path():
    try:
        repository_service.run_repository_analyzers("/this/path/does/not/exist")
    except FileNotFoundError:
        return
    raise AssertionError("Expected FileNotFoundError")
