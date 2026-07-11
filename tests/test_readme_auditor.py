from pathlib import Path

from drrepo.analyzers.readme_auditor import audit_readme


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


def test_good_readme_accepts_synonym_headings_and_code_blocks(tmp_path: Path):
    content = """
# Repo Pilot

Repo Pilot audits Python repositories and explains what should be fixed first.

## Getting Started
Install the package locally:

```bash
pip install -e ".[dev]"
```

## Demo
Run the auditor from the project root:

```bash
drrepo audit .
```

## Prerequisites
Python 3.11+ and Git are required.

## Env Variables
Set `OPENAI_API_KEY` in `.env.local` before enabling AI mode.

## Testing
```bash
pytest
```

## License
MIT
"""
    (tmp_path / "README.md").write_text(content)

    res = audit_readme(tmp_path)

    assert res.status == "completed"
    assert res.summary["missing_sections"] == []
    assert not any(f.code and f.code.startswith("README-MISSING-") for f in res.findings)
    assert not any(f.code == "README-TOO-SHORT" for f in res.findings)


def test_good_readme_accepts_prose_and_code_evidence_without_exact_headings(tmp_path: Path):
    content = """
# Launch Pad

Launch Pad helps small teams audit Python repositories before sharing them.

To get started, install the local package and its dev tools:

```bash
pip install -e ".[dev]"
```

Run the checker from the project root:

```bash
drrepo audit .
```

Requires Python 3.11+ and Git to be available on your machine.
Set `OPENAI_API_KEY` in `.env` before using AI mode.
Validate changes with:

```bash
pytest
```

Released under the MIT license.
"""
    (tmp_path / "README.md").write_text(content)

    res = audit_readme(tmp_path)

    assert res.status == "completed"
    assert res.summary["missing_sections"] == []
    assert not any(f.code and f.code.startswith("README-MISSING-") for f in res.findings)
    assert not any(f.code == "README-TOO-SHORT" for f in res.findings)


def test_short_readme(tmp_path: Path):
    (tmp_path / "README.md").write_text("# My Project")
    res = audit_readme(tmp_path)
    assert res.status == "completed"
    assert any(f.code == "README-TOO-SHORT" for f in res.findings)
    assert res.summary["missing_sections"]


def test_weak_readme_still_stays_incomplete_with_partial_synonym_matches(tmp_path: Path):
    content = """
# Tiny Tool

Small helper for local work.

## Setup
Details coming soon.
"""
    (tmp_path / "README.md").write_text(content)

    res = audit_readme(tmp_path)

    assert res.status == "completed"
    assert "installation" not in res.summary["missing_sections"]
    assert "usage" in res.summary["missing_sections"]
    assert "tests" in res.summary["missing_sections"]
    assert "requirements" in res.summary["missing_sections"]
    assert "environment" in res.summary["missing_sections"]
    assert "license" in res.summary["missing_sections"]
    assert any(f.code == "README-TOO-SHORT" for f in res.findings)


def test_shallow_keyword_mentions_do_not_satisfy_all_sections(tmp_path: Path):
    content = """
# Keyword Soup

This project mentions setup, usage, tests, requirements, configuration, and license,
but the details are intentionally not documented yet.
"""
    (tmp_path / "README.md").write_text(content)

    res = audit_readme(tmp_path)

    assert res.status == "completed"
    assert "installation" in res.summary["missing_sections"]
    assert "usage" in res.summary["missing_sections"]
    assert "tests" in res.summary["missing_sections"]
    assert "requirements" in res.summary["missing_sections"]
    assert "environment" in res.summary["missing_sections"]


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
