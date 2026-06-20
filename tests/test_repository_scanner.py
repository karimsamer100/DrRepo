from __future__ import annotations

from pathlib import Path

from drrepo.scanner.repository_scanner import scan_repository


def test_scanner_on_sample_repo(tmp_path: Path):
    # Create repository layout
    (tmp_path / "README.md").write_text("# title")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'sample'")
    (tmp_path / ".gitignore").write_text("__pycache__/")
    (tmp_path / ".env.example").write_text("TEST=1")

    docs = tmp_path / "docs"
    docs.mkdir()

    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_main.py").write_text("def test_ok():\n    assert True")

    # add python files
    (tmp_path / "main.py").write_text("print('hi')")

    result = scan_repository(tmp_path)
    assert result["status"] == "ok"

    meta = result["metadata"]
    assert meta["python_files"] == 2
    assert meta["test_files"] == 1
    assert meta["has_readme"] is True
    assert meta["has_tests"] is True
    assert meta["has_docs"] is True
    assert meta["has_pyproject"] is True
    assert meta["has_gitignore"] is True
    assert meta["has_env_example"] is True


def test_ignored_folders_not_counted(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('ok')")

    # create ignored folders with files inside
    pyc = tmp_path / "__pycache__"
    pyc.mkdir()
    (pyc / "ignored.py").write_text("# ignored")

    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "ignored.py").write_text("# ignored")

    result = scan_repository(tmp_path)
    assert result["status"] == "ok"
    meta = result["metadata"]
    # only one python file should be counted
    assert meta["python_files"] == 1
    # ignored files should not be included in total_files
    assert meta["total_files"] == 1
