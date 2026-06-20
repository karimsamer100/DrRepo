from pathlib import Path

from drrepo.analyzers.structure_auditor import audit_structure
from drrepo.analyzers.models import ToolFinding


def test_good_structure(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'p'\n")
    (tmp_path / ".gitignore").write_text("venv\n")
    (tmp_path / ".env.example").write_text("ENV=1\n")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("doc")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_app.py").write_text("def test_ok():\n    assert True\n")
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("print('hi')\n")

    res = audit_structure(tmp_path)
    assert res.status == "completed"
    s = res.summary
    assert s["has_tests"] is True
    assert s["has_dependency_file"] is True
    assert s["has_gitignore"] is True
    assert s["has_env_example"] is True
    assert s["has_docs"] is True
    assert "src" in s["source_roots"]
    assert not any(f.code.startswith("STRUCTURE-MISSING") for f in res.findings)


def test_missing_tests(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'p'\n")
    (tmp_path / "app.py").write_text("print('x')\n")
    res = audit_structure(tmp_path)
    assert any(f.code == "STRUCTURE-MISSING-TESTS" for f in res.findings)


def test_missing_dependency_file(tmp_path: Path):
    (tmp_path / "app.py").write_text("print('x')\n")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_app.py").write_text("def test_ok():\n    assert True\n")
    res = audit_structure(tmp_path)
    assert any(f.code == "STRUCTURE-MISSING-DEPENDENCY-FILE" for f in res.findings)


def test_root_source_file(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='p'\n")
    (tmp_path / "main.py").write_text("print('x')\n")
    res = audit_structure(tmp_path)
    assert "." in res.summary["source_roots"]


def test_missing_source_root(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='p'\n")
    res = audit_structure(tmp_path)
    assert any(f.code == "STRUCTURE-MISSING-SOURCE-ROOT" for f in res.findings)


def test_invalid_path():
    try:
        audit_structure("/this/path/does/not/exist")
    except FileNotFoundError:
        return
    raise AssertionError("Expected FileNotFoundError")
