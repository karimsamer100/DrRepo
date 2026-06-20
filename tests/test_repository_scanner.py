from __future__ import annotations

from pathlib import Path

from drrepo.scanner.repository_scanner import scan_repository
from drrepo.input.resolver import find_repository_root


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
    assert meta["total_files"] >= 1
    # invariant: total_files must equal sum of file_extensions counts
    assert meta["total_files"] == sum(meta["file_extensions"].values())


def test_find_repository_root_and_scan_from_nested(tmp_path: Path):
    # Setup project root
    (tmp_path / "pyproject.toml").write_text('[project]\nname="proj"')
    (tmp_path / "README.md").write_text("# readme")

    src = tmp_path / "src"
    (src / "package").mkdir(parents=True)
    (src / "package" / "app.py").write_text("print('ok')")

    # find_repository_root should return the project root when passed nested path
    root = find_repository_root(src / "package")
    assert str(root) == str(tmp_path)

    # scan_repository called on nested folder should report root path and markers
    result = scan_repository(src)
    assert result["status"] == "ok"
    assert result["path"] == str(tmp_path)
    markers = result["metadata"].get("root_markers", [])
    assert "pyproject.toml" in markers
    assert any(m.lower().startswith("readme") for m in markers) or "README.md" in markers


def test_root_markers_listed(tmp_path: Path):
    (tmp_path / "README.md").write_text("# readme")
    (tmp_path / "pyproject.toml").write_text('[project]\nname="a"')
    (tmp_path / "requirements.txt").write_text("flask")

    result = scan_repository(tmp_path)
    markers = set(result["metadata"].get("root_markers", []))
    assert "README.md" in markers or any(m.lower().startswith("readme") for m in markers)
    assert "pyproject.toml" in markers
    assert "requirements.txt" in markers
    # invariant: total_files equals sum of extension counts
    assert result["metadata"]["total_files"] == sum(result["metadata"]["file_extensions"].values())


def test_file_extensions_and_top_levels(tmp_path: Path):
    # create some files and directories
    (tmp_path / "app.py").write_text("print('app')")
    (tmp_path / "README.md").write_text("# r")
    (tmp_path / "Dockerfile").write_text("FROM python")

    src = tmp_path / "src"
    src.mkdir()
    (src / "module.py").write_text("# module")

    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_mod.py").write_text("def test(): pass")

    docs = tmp_path / "docs"
    docs.mkdir()

    # ignored top-level dirs
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "ignored.py").write_text("# x")

    pyc = tmp_path / "__pycache__"
    pyc.mkdir()
    (pyc / "ignored.py").write_text("# y")

    # dependency and config files
    (tmp_path / "pyproject.toml").write_text("[project]\nname='a'")
    (tmp_path / "requirements.txt").write_text("flask")
    (tmp_path / "pytest.ini").write_text("[pytest]")

    # source file at root
    (tmp_path / "root_main.py").write_text("print()")

    result = scan_repository(tmp_path)
    meta = result["metadata"]

    # file extensions
    fe = meta["file_extensions"]
    assert fe.get(".py", 0) >= 2
    assert fe.get(".md", 0) >= 1
    assert fe.get("<no_ext>", 0) >= 1

    # top-level files and directories
    tlf = set(meta["top_level_files"])
    tld = set(meta["top_level_directories"])
    assert "README.md" in tlf
    assert "pyproject.toml" in tlf
    assert "src" in tld and "tests" in tld and "docs" in tld

    # ignored dirs should not appear
    assert ".venv" not in tld

    # dependency and config files
    assert "pyproject.toml" in meta["dependency_files"]
    assert "requirements.txt" in meta["dependency_files"]
    assert "pyproject.toml" in meta["config_files"]
    assert "pytest.ini" in meta["config_files"]

    # source roots
    sr = set(meta["source_roots"])
    assert "." in sr
    assert "src" in sr
    assert "tests" not in sr and "docs" not in sr

    # invariant: total_files equals sum of extension counts
    assert meta["total_files"] == sum(meta["file_extensions"].values())


def test_controlled_repo_counts(tmp_path: Path):
    # Controlled repo with exactly these files
    (tmp_path / "README.md").write_text("# r")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='a'")
    (tmp_path / "app.py").write_text("print('x')")
    (tmp_path / ".gitignore").write_text("__pycache__/")
    (tmp_path / ".env.example").write_text("X=1")

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "README.md").write_text("# d")

    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_app.py").write_text("def test(): pass")

    result = scan_repository(tmp_path)
    meta = result["metadata"]
    # expected files: README.md, pyproject.toml, app.py, .gitignore, .env.example, docs/README.md, tests/test_app.py
    assert meta["total_files"] == 7
    assert meta["total_files"] == sum(meta["file_extensions"].values())


def test_small_bad_repo_counts(tmp_path: Path):
    (tmp_path / "README.md").write_text("# r")
    (tmp_path / "bad.py").write_text("x=1")
    result = scan_repository(tmp_path)
    meta = result["metadata"]
    assert meta["total_files"] == 2
    assert meta["total_files"] == sum(meta["file_extensions"].values())
