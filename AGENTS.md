# DrRepo — Agent Guide

## Commands

```bash
pip install -e ".[dev]"     # dev deps (pytest, ruff, bandit, radon, coverage)
drrepo audit <path>          # --format json|markdown|summary --output <file> --profile <id> --ai
pytest                       # all tests (testpaths = ["tests"] in pyproject.toml)
pytest tests/test_foo.py::test_bar  # single test
ruff check .                 # lint
coverage run -m pytest && coverage report
```

## Architecture

- Entrypoint: `drrepo.cli:app` (Typer CLI)
- Audit pipeline: `input/resolver.py` → `scanner/repository_scanner.py` → `analyzers/service.py` + `test_service.py` + `repository_service.py` → `scoring/scorer.py` → `diagnosis/engine.py` → `remediation/suggestions.py` → reports
- All analyzer results use `ToolResult`/`ToolFinding` dataclasses (`analyzers/models.py`). Allowed statuses: `completed`, `not_available`, `not_applicable`, `skipped_by_config`, `failed_to_run`, `partial`.
- ML subsystem: `drrepo/ml/` (dataset builder, labels, baseline classifier, evaluation, leakage checks). Feature builder: `drrepo/features/`.
- Advisor subsystem: `drrepo/advisor/` — deterministic or AI-driven (LLM router supports gemini, groq, cerebras, openrouter with `.env` fallback chain).
- Python 3.11+, package is `drrepo/` (not `src/` layout).

## Testing quirks

- No conftest.py, no pytest markers, no test classes. Plain `def test_*()` functions.
- Use `monkeypatch` and `tmp_path` builtin fixtures. No decorator fixtures.
- Test data from `tests/fixtures/synthetic_audits.py` — factory functions (`healthy_audit()`, `weak_audit()`, etc.) imported directly.
- Integration tests use `examples/sample_good_repo/` and `examples/sample_bad_repo/` as real audit targets.
- All tests run offline — LLM tests remove env vars and mock HTTP. No API keys required.

## Key constraints

- `.env` (gitignored) holds LLM API keys. Template at `.env.example`.
- No GitHub Actions workflows yet. No pre-commit hooks.
- `.aider*` files are gitignored legacy artifacts.
- No `opencode.json`, `CLAUDE.md`, or `.cursorrules` exist.
