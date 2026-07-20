from pathlib import Path

from drrepo.architecture.engine import build_architecture_assessment


def _audit(root: Path, static_findings: list[dict[str, object]] | None = None) -> dict[str, object]:
    return {
        "path": str(root),
        "static_analysis": [{"tool": "bandit", "status": "completed", "findings": static_findings or []}],
        "test_analysis": [],
        "repository_analysis": [],
        "scoring": {"overall_score": 80},
        "diagnosis": {"repository_health": {"label": "healthy"}},
    }


def _write_layered_fastapi(root: Path) -> None:
    app = root / "app"
    tests = root / "tests"
    app.mkdir()
    tests.mkdir()
    (app / "__init__.py").write_text("", encoding="utf-8")
    (app / "repository.py").write_text("class UserRepository: pass\n", encoding="utf-8")
    (app / "service.py").write_text(
        "from .repository import UserRepository\n\n"
        "def choose(x):\n"
        "    if x == 1: return 'a'\n"
        "    if x == 2: return 'b'\n"
        "    if x == 3: return 'c'\n"
        "    if x == 4: return 'd'\n"
        "    if x == 5: return 'e'\n"
        "    return 'z'\n",
        encoding="utf-8",
    )
    (app / "routes.py").write_text(
        "from fastapi import FastAPI\nfrom .service import choose\napp = FastAPI()\n@app.get('/users')\ndef users(): return choose(1)\n",
        encoding="utf-8",
    )
    (tests / "test_service.py").write_text("from app.service import choose\n\ndef test_choose():\n    assert choose(1) == 'a'\n", encoding="utf-8")


def test_layered_fastapi_graph_classifies_layers_and_entry_points(tmp_path: Path):
    _write_layered_fastapi(tmp_path)

    assessment = build_architecture_assessment(_audit(tmp_path))
    nodes = {node["path"]: node for node in assessment["nodes"]}

    assert assessment["status"] == "completed"
    assert nodes["app/routes.py"]["kind"] == "api_route"
    assert nodes["app/service.py"]["layer"] == "application/service"
    assert nodes["app/repository.py"]["kind"] == "repository/data-access"
    assert any(entry["path"] == "app/routes.py" for entry in assessment["entry_points"])
    assert any(edge["source"] == "node:app.routes" and edge["target"] == "node:app.service" for edge in assessment["edges"])


def test_cycles_and_coupling_are_detected(tmp_path: Path):
    (tmp_path / "a.py").write_text("import b\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("import a\n", encoding="utf-8")

    assessment = build_architecture_assessment(_audit(tmp_path))

    assert assessment["cycles"]
    assert assessment["cycles"][0]["classification"] == "likely architectural cycle"


def test_mixed_frontend_backend_boundary_detects_api_client(tmp_path: Path):
    _write_layered_fastapi(tmp_path)
    frontend = tmp_path / "frontend"
    (frontend / "src").mkdir(parents=True)
    (frontend / "package.json").write_text('{"dependencies":{"react":"latest","axios":"latest"}}', encoding="utf-8")
    (frontend / "src" / "main.tsx").write_text("import axios from 'axios'\naxios.get('/api/users')\n", encoding="utf-8")

    assessment = build_architecture_assessment(_audit(tmp_path))
    frontend_edges = [edge for edge in assessment["edges"] if edge["kind"] == "frontend_calls_api"]

    assert any(node["kind"] == "frontend" for node in assessment["nodes"])
    assert len(frontend_edges) == 1


def test_hotspot_factor_contributions_and_ordering_are_deterministic(tmp_path: Path):
    _write_layered_fastapi(tmp_path)
    findings = [
        {"code": "B608", "message": "SQL risk", "file_path": "app/service.py", "line": 3, "severity": "high"},
        {"code": "RADON-CC", "message": "choose has complexity 12", "file_path": "app/service.py", "line": 3, "severity": "C", "tool": "radon"},
    ]

    first = build_architecture_assessment(_audit(tmp_path, findings))
    second = build_architecture_assessment(_audit(tmp_path, findings))

    assert first["hotspots"][0]["path"] == "app/service.py"
    assert first["hotspots"][0]["factors"]
    assert first["hotspots"] == second["hotspots"]


def test_b101_in_test_file_is_not_ranked_as_production_hotspot(tmp_path: Path):
    _write_layered_fastapi(tmp_path)
    findings = [
        {"code": "B101", "message": "assert used", "file_path": "tests/test_service.py", "line": 3, "severity": "medium"},
    ]

    assessment = build_architecture_assessment(_audit(tmp_path, findings))

    assert all(hotspot["path"] != "tests/test_service.py" for hotspot in assessment["hotspots"])
    test_node = next(node for node in assessment["nodes"] if node["path"] == "tests/test_service.py")
    assert test_node["risk"]["b101_context"] == "expected_test_assert"


def test_b101_in_production_file_contributes_to_hotspot(tmp_path: Path):
    _write_layered_fastapi(tmp_path)
    findings = [
        {"code": "B101", "message": "assert used", "file_path": "app/service.py", "line": 3, "severity": "medium"},
    ]

    assessment = build_architecture_assessment(_audit(tmp_path, findings))

    assert assessment["hotspots"][0]["path"] == "app/service.py"
    assert any(factor["id"] == "findings" for factor in assessment["hotspots"][0]["factors"])


def test_syntax_error_keeps_partial_assessment(tmp_path: Path):
    (tmp_path / "ok.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "broken.py").write_text("def nope(:\n", encoding="utf-8")

    assessment = build_architecture_assessment(_audit(tmp_path))

    assert assessment["status"] == "partial"
    assert assessment["evidence_gaps"]


def test_framework_name_in_text_does_not_create_api_route(tmp_path: Path):
    (tmp_path / "notes.py").write_text("HELP = 'FastAPI appears in a string only'\n", encoding="utf-8")

    assessment = build_architecture_assessment(_audit(tmp_path))
    node = assessment["nodes"][0]

    assert node["kind"] == "module"
    assert not assessment["entry_points"]
