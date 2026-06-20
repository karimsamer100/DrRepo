from pathlib import Path
import json

from drrepo.analyzers.readme_auditor import audit_readme
from drrepo.analyzers.models import ToolResult


def test_missing_readme(tmp_path: Path):
    res = audit_readme(tmp_path)
    assert res.status == "not_applicable"
    assert res.summary["has_readme"] is False
    assert any(f.code == "README-MISSING" for f in res.findings)


def test_good_readme(tmp_path: Path):
    content = """
# My Project

This is a sample project.

## Installation
pip install -r requirements.txt

## Usage
run the app

## Tests
run pytest

## Requirements
requirements.txt

## Environment
create .env

## License
MIT
"""
    (tmp_path / "README.md").write_text(content)
    res = audit_readme(tmp_path)
    assert res.status == "completed"
    assert res.summary["has_readme"] is True
    assert res.summary["missing_sections"] == []
    assert not any("README-MISSING-" in (f.code or "") for f in res.findings)


def test_short_readme(tmp_path: Path):
    (tmp_path / "README.md").write_text("# My Project")
    res = audit_readme(tmp_path)
    assert res.status == "completed"
    assert any(f.code == "README-TOO-SHORT" for f in res.findings)
    assert res.summary["missing_sections"]


def test_alternative_name(tmp_path: Path):
    (tmp_path / "readme.txt").write_text("# Title\nSome description here that is long enough to avoid too short detection." * 3)
    res = audit_readme(tmp_path)
    assert res.status == "completed"
    assert res.summary["has_readme"] is True


def test_invalid_path():
    try:
        audit_readme("/this/path/does/not/exist")
    except FileNotFoundError:
        return
    raise AssertionError("Expected FileNotFoundError")
