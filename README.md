# DrRepo

DrRepo is a local repository audit tool for Python projects. It collects deterministic evidence from linters, security checks, tests, and repository signals, then produces explainable scores and reports in JSON or Markdown.

This repository contains the initial CLI-focused implementation: local folder scanning, deterministic analyzers, a scoring engine, and report renderers.

---

## Current features

- Local repository audit via the CLI
- Repository metadata scanner (file counts, top-level files, source roots)

Static analysis
- Ruff (linting)
- Bandit (security)
- Radon (complexity)

Test analysis
- Pytest
- Coverage (coverage.py)

Repository analysis
- README auditor (checks for common README sections)
- Structure auditor (tests, config files, docs, gitignore, env example)

- Deterministic scoring engine (category scores and overall score)
- JSON output (default)
- Markdown output (via `render_markdown_report`) 
- Optional file output using `--output` (writes JSON or Markdown to disk)

Note: Ruff/Bandit/Radon/Coverage are optional. Missing external tools are reported as `not_available` in the audit results rather than crashing.

---

## Installation / setup (local development)

Create a virtual environment and install the package in editable mode:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -e .
```

Optional tools (install if you want full analyzer outputs):

```powershell
python -m pip install ruff bandit radon coverage
```

Again: these tools are optional. The CLI will report `not_available` for tools that are not installed.

---

## CLI usage

Run a local audit (JSON output by default):

```powershell
python -m drrepo.cli audit examples/sample_good_repo
```

Explicit JSON output:

```powershell
python -m drrepo.cli audit examples/sample_good_repo --format json
```

Markdown output:

```powershell
python -m drrepo.cli audit examples/sample_good_repo --format markdown
```

Write JSON to a file:

```powershell
python -m drrepo.cli audit examples/sample_good_repo --format json --output reports/audit.json
```

Write Markdown to a file:

```powershell
python -m drrepo.cli audit examples/sample_good_repo --format markdown --output reports/audit.md
```

If `--output` is provided the CLI writes the formatted report to disk and prints a short success message; otherwise the report is printed to stdout.

---

## Output structure (JSON)

Top-level keys in the audit JSON:

- `status` — overall run status (e.g. `ok`)
- `path` — resolved repository root path
- `metadata` — repository metadata (file counts, top-level files, markers)
- `static_analysis` — array of analyzer results (ruff, bandit, radon)
- `test_analysis` — array of test/coverage results (pytest, coverage)
- `repository_analysis` — array of repo auditors (readme, structure)
- `scoring` — overall score and per-section scores

Each analyzer entry contains `tool`, `status`, `summary`, `findings`, `errors`, and `raw_output` where available.

---

## Scoring (brief)

- Section scores start from 100.
- Findings subtract deterministic penalties depending on severity (e.g. `critical`, `high`, `medium`, `low`).
- Tools that `failed_to_run` or returned `partial` results receive penalties.
- `not_available` and `not_applicable` statuses are not penalized.

The scoring engine is deterministic and explainable; see the code under `drrepo/scoring` for exact rules.

---

## Development / tests

Run the unit test suite:

```powershell
python -m pytest -q
```

---

## Scope & roadmap

This implementation focuses on local Python repository audits. Future work may include:

- GitHub URL support (clone-and-audit)
- richer report formats and views (HTML, dashboards)
- remediation guidance and optional patch suggestions
- ML/LLM-assisted explanations and remediation planning
- an interactive web UI and CI integrations

---

If you find inaccuracies in this README relative to the code, please open an issue or submit a PR with suggested text.

