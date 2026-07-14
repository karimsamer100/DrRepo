from __future__ import annotations

import json

from drrepo.environment import detect_dependency_environment
from drrepo.intelligence import build_repository_intelligence
from drrepo.reports.markdown_report import render_markdown_report
from drrepo.reports.terminal_summary import render_terminal_summary
from drrepo.scanner.repository_scanner import scan_repository


def _audit_for(path, *, findings=None, diagnosis=None, test_analysis=None):
    scanned = scan_repository(path)
    scanned["dependency_environment"] = detect_dependency_environment(path)
    scanned["static_analysis"] = [
        {
            "tool": "ruff",
            "status": "completed",
            "findings": findings or [],
            "errors": [],
            "analysis_outcome": "findings_present" if findings else "clean",
        }
    ]
    scanned["test_analysis"] = test_analysis or []
    scanned["repository_analysis"] = []
    scanned["scoring"] = {"overall_score": 88, "categories": {"testing": 70}}
    scanned["diagnosis"] = diagnosis or {
        "repository_health": {"label": "healthy", "summary": "Observed evidence is healthy."},
        "hard_flags": [],
        "limitations": [],
        "evidence_confidence": {"label": "partial", "summary": "Some optional evidence is unavailable."},
    }
    return scanned


def test_detects_fastapi_api_entrypoint_and_runnability(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "api-demo"
dependencies = ["fastapi", "uvicorn"]
""",
        encoding="utf-8",
    )
    (tmp_path / "app.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    result = build_repository_intelligence(_audit_for(tmp_path))
    identity = result["project_understanding"]["project_identity"]
    entry_points = result["project_understanding"]["entry_points"]
    runnability = result["project_understanding"]["runnability"]

    assert identity["project_type"] == "FastAPI API"
    assert "FastAPI" in identity["frameworks"]
    assert any(entry["kind"] == "api" and entry["path"] == "app.py" for entry in entry_points)
    assert "python -m pip install -e ." in runnability["install_commands"]
    assert "python -m pytest" in runnability["test_commands"]


def test_detects_mixed_backend_frontend_project(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='mixed'\n", encoding="utf-8")
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "api.py").write_text("from flask import Flask\napp = Flask(__name__)\n", encoding="utf-8")
    (tmp_path / "package.json").write_text(json.dumps({"scripts": {"dev": "vite", "build": "vite build"}}), encoding="utf-8")

    result = build_repository_intelligence(_audit_for(tmp_path))
    identity = result["project_understanding"]["project_identity"]
    architecture = result["project_understanding"]["architecture_summary"]

    assert identity["project_type"] == "backend + frontend application"
    assert "Flask application" in identity["secondary_project_types"]
    assert architecture["backend_present"] is True
    assert architecture["frontend_present"] is True


def test_detects_cli_library_from_pyproject_scripts(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "cli-demo"

[project.scripts]
demo = "cli_demo.cli:main"
""",
        encoding="utf-8",
    )
    (tmp_path / "cli_demo").mkdir()
    (tmp_path / "cli_demo" / "cli.py").write_text("def main():\n    pass\n", encoding="utf-8")

    result = build_repository_intelligence(_audit_for(tmp_path))
    identity = result["project_understanding"]["project_identity"]
    entry_points = result["project_understanding"]["entry_points"]

    assert identity["project_type"] == "CLI tool"
    assert "CLI" in identity["interfaces"]
    assert any(entry["command"] == "demo" and entry["symbol"] == "cli_demo.cli:main" for entry in entry_points)


def test_detects_ml_and_rag_signals_without_importing_code(tmp_path):
    (tmp_path / "train.py").write_text(
        "import torch\nfrom langchain.schema import Document\n\ndef train():\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "data").mkdir()

    result = build_repository_intelligence(_audit_for(tmp_path))
    identity = result["project_understanding"]["project_identity"]

    assert "ML training project" in [identity["project_type"], *identity["secondary_project_types"]]
    assert "RAG/LLM application" in [identity["project_type"], *identity["secondary_project_types"]]
    assert "PyTorch" in identity["frameworks"]
    assert "LangChain" in identity["frameworks"]


def test_executive_report_does_not_contradict_diagnosis(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    diagnosis = {
        "repository_health": {"label": "needs_attention", "summary": "Hard blockers exist."},
        "hard_flags": ["TESTS_FAILING"],
        "limitations": ["coverage skipped"],
        "evidence_confidence": {"label": "limited", "summary": "Limited evidence."},
    }

    result = build_repository_intelligence(_audit_for(tmp_path, diagnosis=diagnosis))
    report = result["executive_report"]

    assert report["verdict"] == "needs_attention"
    assert report["evidence_confidence"] == "limited"
    assert "needs attention" in report["one_sentence_summary"]


def test_recommendations_group_readme_ruff_and_audit_environment(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    findings = [
        {"tool": "readme", "code": "README-MISSING-TESTING", "message": "Missing testing"},
        {"tool": "readme", "code": "README-MISSING-LICENSE", "message": "Missing license"},
        {"tool": "ruff", "code": "F401", "message": "unused import"},
    ]
    audit = _audit_for(tmp_path, findings=findings)
    audit["static_analysis"].append(
        {
            "tool": "radon",
            "status": "failed_to_run",
            "findings": [],
            "errors": ["runner failed"],
            "analysis_outcome": "execution_failed",
        }
    )

    result = build_repository_intelligence(audit)
    recommendations = result["recommendations_v2"]
    titles = [rec["title"] for rec in recommendations]

    assert titles.count("Document setup, testing, and project context") == 1
    assert "Resolve grouped Ruff code-quality findings" in titles
    assert any(rec["recommendation_type"] == "audit_environment" for rec in recommendations)


def test_profile_specific_ranking_changes_priority(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    findings = [
        {"tool": "readme", "code": "README-MISSING-TESTING", "message": "Missing testing"},
        {"tool": "bandit", "code": "B101", "message": "assert used"},
    ]
    audit = _audit_for(tmp_path, findings=findings)

    student = build_repository_intelligence(audit, profile_id="student_portfolio")["recommendations_v2"]
    production = build_repository_intelligence(audit, profile_id="production_service")["recommendations_v2"]

    assert student[0]["category"] == "documentation"
    assert production[0]["category"] == "security"


def test_supported_profiles_include_production_api_and_ai_ml_project(tmp_path):
    (tmp_path / "train.py").write_text("import sklearn\n", encoding="utf-8")
    audit = _audit_for(tmp_path, findings=[{"tool": "readme", "code": "README-MISSING-TESTING", "message": "Missing testing"}])

    api_result = build_repository_intelligence(audit, profile_id="production_api")
    ml_result = build_repository_intelligence(audit, profile_id="ai_ml_project")

    assert "production" in api_result["executive_report"]["user_profile_context"].lower()
    assert "reproducible" in ml_result["executive_report"]["user_profile_context"].lower()


def test_reports_include_executive_identity_and_top_actions(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    audit = _audit_for(tmp_path, findings=[{"tool": "ruff", "code": "F401", "message": "unused"}])
    audit.update(build_repository_intelligence(audit))

    markdown = render_markdown_report(audit)
    terminal = render_terminal_summary(audit)

    assert "## Executive Summary" in markdown
    assert "## Project Identity" in markdown
    assert "## How to Run / Runnability" in markdown
    assert "## Top Actions" in markdown
    assert "Project type:" in terminal
    assert "Next best step:" in terminal


def test_project_understanding_does_not_import_repository_code(tmp_path):
    (tmp_path / "app.py").write_text(
        "raise RuntimeError('imported unsafe code')\nfrom fastapi import FastAPI\napp = FastAPI()\n",
        encoding="utf-8",
    )

    result = build_repository_intelligence(_audit_for(tmp_path))

    assert result["project_understanding"]["project_identity"]["project_type"] == "FastAPI API"
