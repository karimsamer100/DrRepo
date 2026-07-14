from __future__ import annotations

import json
from pathlib import Path

from drrepo.audit import build_audit
from drrepo.environment import detect_dependency_environment
from drrepo.intelligence import build_repository_intelligence
from drrepo.readiness import build_devops_readiness
from drrepo.reports.markdown_report import render_markdown_report
from drrepo.reports.terminal_summary import render_terminal_summary
from drrepo.scanner.repository_scanner import scan_repository


def _base_audit(path: Path, *, profile_id: str = "production_api") -> dict:
    audit = scan_repository(path)
    audit["dependency_environment"] = detect_dependency_environment(path)
    audit["static_analysis"] = []
    audit["test_analysis"] = []
    audit["repository_analysis"] = []
    audit["scoring"] = {"overall_score": 90}
    audit["diagnosis"] = {
        "repository_health": {"label": "healthy", "summary": "ok"},
        "hard_flags": [],
        "limitations": [],
        "evidence_confidence": {"label": "partial", "summary": "partial"},
    }
    audit.update(build_repository_intelligence(audit, profile_id=profile_id))
    return audit


def _write_strong_fastapi(root: Path) -> None:
    (root / "app").mkdir()
    (root / "tests").mkdir()
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        "[project]\nname='svc'\nversion='1.0.0'\nrequires-python='>=3.11'\ndependencies=['fastapi','uvicorn']\n",
        encoding="utf-8",
    )
    (root / "uv.lock").write_text("lock", encoding="utf-8")
    (root / "LICENSE").write_text("MIT", encoding="utf-8")
    (root / ".env.example").write_text("DATABASE_URL=\n", encoding="utf-8")
    (root / ".gitignore").write_text(".env\n", encoding="utf-8")
    (root / "app" / "main.py").write_text(
        "import logging\nfrom fastapi import FastAPI\napp = FastAPI()\n@app.get('/health')\ndef health(): return {'ok': True}\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_app.py").write_text("def test_ok(): assert True\n", encoding="utf-8")
    (root / ".github" / "workflows" / "ci.yml").write_text(
        """
on: [push, pull_request]
permissions:
  contents: read
concurrency:
  group: ci-${{ github.ref }}
jobs:
  test:
    timeout-minutes: 10
    strategy:
      matrix:
        python-version: ["3.11"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: uv sync
      - run: ruff check .
      - run: bandit -r app
      - run: pytest --cov
      - run: coverage report
      - uses: actions/upload-artifact@v4
""",
        encoding="utf-8",
    )
    (root / "Dockerfile").write_text(
        "FROM python:3.12-slim\nWORKDIR /app\nCOPY pyproject.toml uv.lock ./\nRUN pip install uv\nCOPY . .\nUSER 10001\nHEALTHCHECK CMD python -c \"print('ok')\"\nCMD [\"uvicorn\", \"app.main:app\", \"--host\", \"0.0.0.0\"]\n",
        encoding="utf-8",
    )
    (root / ".dockerignore").write_text(".env\n.venv\n__pycache__\n", encoding="utf-8")
    (root / "render.yaml").write_text("services:\n- type: web\n  startCommand: uvicorn app.main:app\n", encoding="utf-8")


def test_strong_production_fastapi_nearly_or_release_ready(tmp_path: Path):
    _write_strong_fastapi(tmp_path)
    readiness = build_devops_readiness(_base_audit(tmp_path), profile_id="production_api")

    assert readiness["verdict"] in {"release_ready", "nearly_ready"}
    assert readiness["observed_score"] >= 75
    assert readiness["blockers"] == []
    assert _dimension(readiness, "ci_cd")["status"] == "ready"
    assert _dimension(readiness, "containerization")["score"] is not None


def test_weak_production_api_has_release_blockers(tmp_path: Path):
    (tmp_path / "app.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\nDEBUG=True\n",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text("API_KEY=fake_test_token_1234567890abcdef\n", encoding="utf-8")
    audit = _base_audit(tmp_path, profile_id="production_api")

    readiness = build_devops_readiness(audit, profile_id="production_api")

    assert readiness["verdict"] == "blocked"
    blocker_ids = {item["id"] for item in readiness["blockers"]}
    assert "ci.missing" in blocker_ids
    assert "config.committed-env-secret" in blocker_ids
    assert "fake_test_token" not in json.dumps(readiness)


def test_ignored_local_env_is_not_reported_as_committed_secret(tmp_path: Path):
    (tmp_path / "app.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")
    (tmp_path / ".env").write_text("API_KEY=fake_test_token_1234567890abcdef\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(".env\n", encoding="utf-8")

    readiness = build_devops_readiness(_base_audit(tmp_path), profile_id="production_api")

    dumped = json.dumps(readiness)
    blocker_ids = {item["id"] for item in readiness["blockers"]}
    assert "config.committed-env-secret" not in blocker_ids
    assert "config.committed-env" not in dumped
    assert "fake_test_token" not in dumped


def test_python_library_excludes_deployment_and_container_penalty(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='lib'\nversion='0.1.0'\n[project.scripts]\nlib='lib.cli:main'\n",
        encoding="utf-8",
    )
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "cli.py").write_text("def main(): pass\n", encoding="utf-8")
    readiness = build_devops_readiness(_base_audit(tmp_path, profile_id="open_source_library"), profile_id="open_source_library")

    assert _dimension(readiness, "deployment")["applicability"] == "not_applicable"
    assert _dimension(readiness, "containerization")["applicability"] == "not_applicable"
    assert readiness["observed_score"] is not None


def test_backend_frontend_ci_detects_missing_frontend_build(tmp_path: Path):
    _write_strong_fastapi(tmp_path)
    (tmp_path / "package.json").write_text(json.dumps({"scripts": {"build": "vite build"}}), encoding="utf-8")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    ci = tmp_path / ".github" / "workflows" / "ci.yml"
    ci.write_text("on: [pull_request]\njobs:\n  test:\n    steps:\n      - uses: actions/checkout@v4\n      - run: pytest\n", encoding="utf-8")
    readiness = build_devops_readiness(_base_audit(tmp_path), profile_id="production_api")

    findings = _dimension(readiness, "ci_cd")["findings"]
    assert any(item["id"] == "ci.no-frontend-build" for item in findings)


def test_frontend_dev_script_is_not_deployment_blocker_without_deploy_config(tmp_path: Path):
    (tmp_path / "app.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")
    (tmp_path / "package.json").write_text(json.dumps({"scripts": {"dev": "vite --host", "build": "vite build"}}), encoding="utf-8")

    readiness = build_devops_readiness(_base_audit(tmp_path), profile_id="production_api")

    blocker_ids = {item["id"] for item in _dimension(readiness, "deployment")["blockers"]}
    assert "deploy.dev-server" not in blocker_ids


def test_readiness_rule_strings_do_not_create_self_detection_blockers(tmp_path: Path):
    (tmp_path / "app.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")
    (tmp_path / "drrepo" / "readiness").mkdir(parents=True)
    (tmp_path / "drrepo" / "readiness" / "engine.py").write_text("PATTERN = 'debug=True'\n", encoding="utf-8")

    readiness = build_devops_readiness(_base_audit(tmp_path), profile_id="production_api")

    blocker_ids = {item["id"] for item in _dimension(readiness, "configuration_security")["blockers"]}
    assert "config.debug-true" not in blocker_ids


def test_ai_ml_reproducibility_flags_missing_artifact_handling(tmp_path: Path):
    (tmp_path / "train.py").write_text("import sklearn\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("scikit-learn\n", encoding="utf-8")
    readiness = build_devops_readiness(_base_audit(tmp_path, profile_id="ai_ml_project"), profile_id="ai_ml_project")

    repro = _dimension(readiness, "reproducibility")
    assert "dataset/model artifact handling" in repro["unverified_checks"]


def test_notebook_does_not_disable_api_devops_applicability(tmp_path: Path):
    (tmp_path / "app.py").write_text("from fastapi import FastAPI\napp=FastAPI()\n", encoding="utf-8")
    (tmp_path / "exploration.ipynb").write_text("{}", encoding="utf-8")

    readiness = build_devops_readiness(_base_audit(tmp_path, profile_id="production_api"), profile_id="production_api")

    assert _dimension(readiness, "deployment")["applicability"] == "applicable"
    assert _dimension(readiness, "observability")["applicability"] == "applicable"


def test_dockerfile_checks_non_root_healthcheck_and_dockerignore(tmp_path: Path):
    (tmp_path / "app.py").write_text("from fastapi import FastAPI\napp=FastAPI()\n", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM python\nCOPY . .\nCMD python app.py\n", encoding="utf-8")
    readiness = build_devops_readiness(_base_audit(tmp_path), profile_id="production_api")

    container = _dimension(readiness, "containerization")
    finding_ids = {item["id"] for item in container["findings"]}
    assert {"container.unpinned-base", "container.root-user", "container.broad-copy"}.issubset(finding_ids)


def test_devops_readiness_is_in_build_audit_contract(tmp_path: Path):
    _write_strong_fastapi(tmp_path)
    audit = build_audit(tmp_path, analysis_mode="quick_safe", profile_id="production_api")

    assert "devops_readiness" in audit
    assert audit["devops_readiness"]["dimensions"]
    assert any(rec["id"].startswith("devops-") for rec in audit["recommendations_v2"])


def test_release_blockers_rank_before_general_repository_fixes(tmp_path: Path):
    (tmp_path / "app.py").write_text(
        "from fastapi import FastAPI\napp=FastAPI()\nDEBUG=True\n",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text("API_KEY=fake_test_token_1234567890abcdef\n", encoding="utf-8")

    audit = build_audit(tmp_path, analysis_mode="quick_safe", profile_id="production_api")

    assert audit["recommendations_v2"][0]["recommendation_type"] == "release_blocker"


def test_markdown_and_terminal_include_devops_readiness(tmp_path: Path):
    _write_strong_fastapi(tmp_path)
    audit = _base_audit(tmp_path)
    audit["devops_readiness"] = build_devops_readiness(audit, profile_id="production_api")

    markdown = render_markdown_report(audit)
    terminal = render_terminal_summary(audit)

    assert "## DevOps & Release Readiness" in markdown
    assert "### Readiness dimensions" in markdown
    assert "DevOps readiness:" in terminal


def test_static_readiness_does_not_import_repository_code(tmp_path: Path):
    (tmp_path / "app.py").write_text(
        "raise RuntimeError('do not import')\nfrom fastapi import FastAPI\napp=FastAPI()\n",
        encoding="utf-8",
    )
    readiness = build_devops_readiness(_base_audit(tmp_path), profile_id="production_api")
    assert readiness["applicability"] == "applicable"


def test_isolated_test_evidence_strengthens_reproducibility(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='svc'\n", encoding="utf-8")
    audit = _base_audit(tmp_path, profile_id="production_api")
    audit["test_analysis"] = [
        {
            "tool": "pytest",
            "status": "completed",
            "execution_mode": "deep_isolated",
            "summary": {"outcome": "passed"},
            "findings": [],
        },
        {
            "tool": "coverage",
            "status": "completed",
            "execution_mode": "deep_isolated",
            "summary": {"coverage_percent": 92.0},
            "findings": [],
        },
    ]

    readiness = build_devops_readiness(audit, profile_id="production_api")
    repro = _dimension(readiness, "reproducibility")

    assert "Tests passed inside the isolated Docker runner." in repro["strengths"]
    assert "Coverage was measured inside the isolated Docker runner." in repro["strengths"]


def test_isolated_docker_unavailable_is_reproducibility_gap_not_blocker(tmp_path: Path):
    audit = _base_audit(tmp_path, profile_id="production_api")
    audit["test_analysis"] = [
        {
            "tool": "pytest",
            "status": "not_available",
            "execution_mode": "deep_isolated",
            "summary": {"outcome": "docker_unavailable"},
            "findings": [],
        }
    ]

    readiness = build_devops_readiness(audit, profile_id="production_api")
    repro = _dimension(readiness, "reproducibility")

    assert "Docker isolated runner availability" in repro["unverified_checks"]
    assert all(item["id"] != "Docker isolated runner availability" for item in readiness["blockers"])


def _dimension(readiness: dict, dimension_id: str) -> dict:
    return next(item for item in readiness["dimensions"] if item["id"] == dimension_id)
