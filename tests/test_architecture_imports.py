from pathlib import Path

from drrepo.architecture.imports import collect_python_import_graph, module_name_for_path


def test_ast_import_extraction_and_relative_resolution(tmp_path: Path):
    pkg = tmp_path / "app"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "repository.py").write_text("class Repo: pass\n", encoding="utf-8")
    (pkg / "service.py").write_text(
        "import requests\nfrom .repository import Repo\nfrom app import repository\n",
        encoding="utf-8",
    )

    modules, errors = collect_python_import_graph(tmp_path)
    service = next(module for module in modules if module.path == "app/service.py")

    assert errors == []
    assert "app.repository" in service.internal_imports
    assert "requests" in service.external_imports


def test_no_execution_when_collecting_import_graph(tmp_path: Path):
    marker = tmp_path / "executed.txt"
    (tmp_path / "danger.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n",
        encoding="utf-8",
    )

    modules, errors = collect_python_import_graph(tmp_path)

    assert len(modules) == 1
    assert errors == []
    assert not marker.exists()


def test_syntax_error_produces_partial_module_evidence(tmp_path: Path):
    (tmp_path / "broken.py").write_text("def nope(:\n", encoding="utf-8")

    modules, errors = collect_python_import_graph(tmp_path)

    assert modules[0].syntax_error
    assert errors


def test_module_name_normalizes_src_and_init(tmp_path: Path):
    path = tmp_path / "src" / "pkg" / "__init__.py"
    path.parent.mkdir(parents=True)
    path.write_text("", encoding="utf-8")

    assert module_name_for_path(path, tmp_path) == "pkg"
