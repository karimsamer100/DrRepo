from __future__ import annotations

import importlib
import os
import shutil
import stat
from pathlib import Path

from fastapi.testclient import TestClient

import drrepo.api.app as app_module
from drrepo.api.app import app

client = TestClient(app)

SAMPLE_GOOD_REPO = str(Path(__file__).resolve().parent.parent / "examples" / "sample_good_repo")


def _make_client(monkeypatch, dist_path: str | None):
    """Create a fresh TestClient with the requested frontend dist path."""
    if dist_path is not None:
        monkeypatch.setenv("DRREPO_FRONTEND_DIST", dist_path)
    else:
        monkeypatch.delenv("DRREPO_FRONTEND_DIST", raising=False)
    importlib.reload(app_module)
    return TestClient(app_module.app)


def _mock_github_clone(monkeypatch, workspace: Path, source_repo: str):
    """Patch workspace helpers so GitHub URL audits clone a local fixture."""
    repo_path = workspace / "repo"

    def fake_create_temp_workspace(prefix: str = "drrepo-") -> Path:
        return workspace

    def fake_clone_public_github_repo(url: str, workspace_path: Path, timeout_seconds: int = 60) -> Path:
        shutil.copytree(source_repo, repo_path)
        return repo_path

    def fake_cleanup_workspace(path: Path) -> None:
        return

    monkeypatch.setattr("drrepo.input.workspace.create_temp_workspace", fake_create_temp_workspace)
    monkeypatch.setattr("drrepo.input.workspace.clone_public_github_repo", fake_clone_public_github_repo)
    monkeypatch.setattr("drrepo.input.workspace.cleanup_workspace", fake_cleanup_workspace)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


def test_profiles():
    response = client.get("/api/profiles")
    assert response.status_code == 200
    data = response.json()
    assert len(data["profiles"]) >= 1
    profile_ids = [p["profile_id"] for p in data["profiles"]]
    assert "student_portfolio" in profile_ids


def test_capabilities_endpoint():
    response = client.get("/api/capabilities")
    assert response.status_code == 200
    data = response.json()
    modes = {mode["id"]: mode for mode in data["supported_analysis_modes"]}
    analyzers = {entry["analyzer_id"]: entry for entry in data["analyzers"]}
    assert modes["quick_safe"]["executes_repository_code"] is False
    assert modes["deep_local"]["supported_source_types"] == ["local_path"]
    assert modes["deep_isolated"]["supported_source_types"] == ["local_path", "github_url"]
    assert analyzers["pytest"]["executes_repository_code"] is True
    assert analyzers["ci_config"]["executes_repository_code"] is False
    assert analyzers["container_config"]["section"] == "readiness"
    assert ".[analysis]" in data["setup"]["install_command"]
    assert "supported" in data["docker_isolated_execution"]
    ai_cap = data.get("ai_advisor")
    assert ai_cap is not None
    assert ai_cap["supported"] is True
    assert ai_cap["deterministic_fallback_available"] is True
    assert ai_cap["explicit_opt_in_required"] is True
    assert "privacy_note" in ai_cap
    assert "provider_routes" in ai_cap


def test_audit_local_path_success():
    response = client.post(
        "/api/audits",
        json={"source_type": "local_path", "source_value": SAMPLE_GOOD_REPO},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["source_type"] == "local_path"
    assert data["analysis_mode"] == "deep_local"
    assert data["audit"]["analysis"]["mode"] == "deep_local"
    assert data["profile_id"] == "student_portfolio"
    assert "audit" in data
    assert "advisor" in data
    assert "project_understanding" in data["audit"]
    assert "executive_report" in data["audit"]
    assert "recommendations_v2" in data["audit"]
    assert "devops_readiness" in data["audit"]
    assert data["audit"]["executive_report"]["verdict"] == data["audit"]["diagnosis"]["repository_health"]["label"]
    assert data["markdown"] is None


def test_audit_local_path_not_found():
    response = client.post(
        "/api/audits",
        json={
            "source_type": "local_path",
            "source_value": "/no/such/path/anywhere",
        },
    )
    assert response.status_code == 400


def test_audit_unsupported_source_type():
    response = client.post(
        "/api/audits",
        json={
            "source_type": "s3_url",
            "source_value": "s3://bucket/repo",
        },
    )
    assert response.status_code == 422


def test_audit_github_url_success(monkeypatch, tmp_path: Path):
    _mock_github_clone(monkeypatch, tmp_path, SAMPLE_GOOD_REPO)
    response = client.post(
        "/api/audits",
        json={
            "source_type": "github_url",
            "source_value": "https://github.com/owner/repo",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["source_type"] == "github_url"
    assert data["analysis_mode"] == "quick_safe"
    assert data["audit"]["analysis"]["mode"] == "quick_safe"
    assert data["source_value"] == "https://github.com/owner/repo"
    assert data["audit"]["source"]["value"] == "https://github.com/owner/repo"
    assert "audit" in data
    test_statuses = {entry["tool"]: entry["status"] for entry in data["audit"]["test_analysis"]}
    assert test_statuses == {"pytest": "skipped_by_config", "coverage": "skipped_by_config"}
    assert data["audit"]["scoring"]["categories"]["testing"] < 100
    assert data["audit"]["diagnosis"]["evidence_confidence"]["label"] in {"partial", "limited"}
    assert data["audit"]["diagnosis"]["evidence_confidence"]["skipped_optional_tools"] == ["coverage", "pytest"]
    assert "Skipped for remote GitHub audit safety." in data["audit"]["diagnosis"]["limitations"]


def test_audit_github_url_rejects_deep_local():
    response = client.post(
        "/api/audits",
        json={
            "source_type": "github_url",
            "source_value": "https://github.com/owner/repo",
            "analysis_mode": "deep_local",
        },
    )
    assert response.status_code == 400
    assert "deep_local" in response.json()["detail"]


def test_audit_deep_isolated_rejects_when_docker_unavailable(monkeypatch):
    from drrepo.execution.docker_runner import DockerCapability

    monkeypatch.setattr(
        "drrepo.execution.check_docker_capability",
        lambda: DockerCapability(False, False, None, "image", False, False, "Docker CLI is not installed."),
    )
    response = client.post(
        "/api/audits",
        json={
            "source_type": "local_path",
            "source_value": SAMPLE_GOOD_REPO,
            "analysis_mode": "deep_isolated",
        },
    )

    assert response.status_code == 400
    assert "Docker CLI" in response.json()["detail"]


def test_audit_local_quick_safe_skips_test_execution():
    response = client.post(
        "/api/audits",
        json={
            "source_type": "local_path",
            "source_value": SAMPLE_GOOD_REPO,
            "analysis_mode": "quick_safe",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["analysis_mode"] == "quick_safe"
    test_statuses = {entry["tool"]: entry["status"] for entry in data["audit"]["test_analysis"]}
    assert test_statuses == {"pytest": "skipped_by_config", "coverage": "skipped_by_config"}


def test_audit_github_url_with_git_suffix_success(monkeypatch, tmp_path: Path):
    _mock_github_clone(monkeypatch, tmp_path, SAMPLE_GOOD_REPO)
    response = client.post(
        "/api/audits",
        json={
            "source_type": "github_url",
            "source_value": "https://github.com/owner/repo.git",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source_type"] == "github_url"


def test_audit_github_url_invalid():
    response = client.post(
        "/api/audits",
        json={
            "source_type": "github_url",
            "source_value": "not-a-url",
        },
    )
    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "github" in detail or "invalid" in detail


def test_audit_github_url_non_github():
    response = client.post(
        "/api/audits",
        json={
            "source_type": "github_url",
            "source_value": "https://gitlab.com/owner/repo",
        },
    )
    assert response.status_code == 400


def test_audit_github_url_ssh_scheme_rejected():
    response = client.post(
        "/api/audits",
        json={
            "source_type": "github_url",
            "source_value": "git@github.com:owner/repo.git",
        },
    )
    assert response.status_code == 400


def test_audit_github_url_file_scheme_rejected():
    response = client.post(
        "/api/audits",
        json={
            "source_type": "github_url",
            "source_value": "file:///etc/passwd",
        },
    )
    assert response.status_code == 400


def test_audit_github_url_clone_failure(monkeypatch, tmp_path: Path):
    def fake_create_temp_workspace(prefix: str = "drrepo-") -> Path:
        return tmp_path

    def fake_clone_public_github_repo(url: str, workspace_path: Path, timeout_seconds: int = 60) -> Path:
        raise RuntimeError("git clone failed: repository not found")

    def fake_cleanup_workspace(path: Path) -> None:
        return

    monkeypatch.setattr("drrepo.input.workspace.create_temp_workspace", fake_create_temp_workspace)
    monkeypatch.setattr("drrepo.input.workspace.clone_public_github_repo", fake_clone_public_github_repo)
    monkeypatch.setattr("drrepo.input.workspace.cleanup_workspace", fake_cleanup_workspace)

    response = client.post(
        "/api/audits",
        json={
            "source_type": "github_url",
            "source_value": "https://github.com/owner/missing-repo",
        },
    )
    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "clone" in detail or "not found" in detail


def test_audit_ai_supported_and_returns_typed_fallback_when_unconfigured(monkeypatch, tmp_path: Path):
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY", "CEREBRAS_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    response = client.post(
        "/api/audits",
        json={
            "source_type": "local_path",
            "source_value": str(tmp_path),
            "ai": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    ai_advisor = data.get("ai_advisor") or {}
    assert ai_advisor.get("requested") is True
    assert ai_advisor.get("source") == "deterministic"
    assert ai_advisor.get("status") in {
        "provider_not_configured",
        "provider_unavailable",
        "fallback",
    }
    assert ai_advisor.get("advisor_response") is not None
    # Core audit is still present and successful
    assert data.get("status") == "ok"
    assert data.get("audit") is not None


def test_audit_ai_false_regression(tmp_path: Path):
    response = client.post(
        "/api/audits",
        json={
            "source_type": "local_path",
            "source_value": str(tmp_path),
            "ai": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    ai_advisor = data.get("ai_advisor") or {}
    assert ai_advisor.get("requested") is False
    assert ai_advisor.get("source") == "deterministic"
    assert ai_advisor.get("status") == "not_requested"


def test_audit_include_markdown_success(tmp_path: Path):
    response = client.post(
        "/api/audits",
        json={
            "source_type": "local_path",
            "source_value": str(tmp_path),
            "include_markdown": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    markdown = data.get("markdown")
    assert markdown is not None
    assert "# DrRepo Audit Report" in markdown
    assert "## Executive Summary" in markdown
    assert "## Project Identity" in markdown
    assert "## Top Actions" in markdown


def test_audit_github_url_markdown_prefers_original_source(monkeypatch, tmp_path: Path):
    _mock_github_clone(monkeypatch, tmp_path, SAMPLE_GOOD_REPO)
    response = client.post(
        "/api/audits",
        json={
            "source_type": "github_url",
            "source_value": "https://github.com/owner/repo",
            "include_markdown": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["audit"]["path"] == str(tmp_path / "repo")
    assert data["markdown"] is not None
    assert "https://github.com/owner/repo" in data["markdown"]
    assert str(tmp_path / "repo") not in data["markdown"]


def test_audit_invalid_profile_id(tmp_path: Path):
    response = client.post(
        "/api/audits",
        json={
            "source_type": "local_path",
            "source_value": str(tmp_path),
            "profile_id": "nonexistent_profile",
        },
    )
    assert response.status_code == 400


def test_advisor_response_safety():
    response = client.post(
        "/api/audits",
        json={"source_type": "local_path", "source_value": SAMPLE_GOOD_REPO},
    )
    assert response.status_code == 200
    data = response.json()
    advisor = data.get("advisor") or {}

    def _flatten_keys(d, path=""):
        for k, v in (d.items() if isinstance(d, dict) else []):
            key = f"{path}.{k}" if path else k
            yield key
            if isinstance(v, dict):
                yield from _flatten_keys(v, key)
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    if isinstance(item, dict):
                        yield from _flatten_keys(item, f"{key}[{i}]")

    keys = set(_flatten_keys(advisor))
    sensitive = {"prompt_bundle", "api_key", "token", "authorization", "raw_response", "prompt", "apiKey"}
    found = keys & sensitive
    assert not found, f"Advisor response exposes sensitive keys: {found}"


def test_cors_allows_dev_origin():
    origin = "http://localhost:5173"
    response = client.options(
        "/api/profiles",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin

    get_response = client.get("/api/profiles", headers={"Origin": origin})
    assert get_response.headers.get("access-control-allow-origin") == origin


def test_root_serves_index_when_dist_exists(tmp_path: Path, monkeypatch):
    index = tmp_path / "index.html"
    index.write_text("<!doctype html><html><body>DrRepo</body></html>", encoding="utf-8")

    test_client = _make_client(monkeypatch, str(tmp_path))
    response = test_client.get("/")
    assert response.status_code == 200
    assert "DrRepo" in response.text


def test_static_assets_served_when_dist_exists(tmp_path: Path, monkeypatch):
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("console.log('drrepo')", encoding="utf-8")
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")

    test_client = _make_client(monkeypatch, str(tmp_path))
    response = test_client.get("/assets/app.js")
    assert response.status_code == 200
    assert "drrepo" in response.text
    assert response.headers.get("content-type") == "text/javascript; charset=utf-8"


def test_spa_fallback_returns_index(tmp_path: Path, monkeypatch):
    index = tmp_path / "index.html"
    index.write_text("<!doctype html><html><body>SPA</body></html>", encoding="utf-8")

    test_client = _make_client(monkeypatch, str(tmp_path))
    response = test_client.get("/some/spa/route")
    assert response.status_code == 200
    assert "SPA" in response.text


def test_missing_dist_root_message(tmp_path: Path, monkeypatch):
    missing_dist = tmp_path / "not_a_dist"
    test_client = _make_client(monkeypatch, str(missing_dist))
    response = test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Frontend build not found" in data["message"]
    assert "npm run build" in data["message"]


def test_cleanup_workspace_removes_read_only_files(tmp_path: Path):
    from drrepo.input.workspace import cleanup_workspace

    d = tmp_path / "readonly_dir"
    d.mkdir()
    f = d / "readonly.idx"
    f.write_text("packed")
    os.chmod(f, stat.S_IREAD)  # Remove write permission
    os.chmod(d, stat.S_IREAD | stat.S_IXUSR)  # Remove write on dir

    cleanup_workspace(d)
    assert not d.exists()


def test_cleanup_workspace_silent_on_missing(tmp_path: Path):
    from drrepo.input.workspace import cleanup_workspace

    missing = tmp_path / "does_not_exist"
    cleanup_workspace(missing)  # Should not raise


def test_audit_github_url_cleanup_failure_still_returns_200(
    monkeypatch, tmp_path: Path
):
    """Simulate a PermissionError during cleanup after a successful clone+audit."""
    repo_path = tmp_path / "repo"
    shutil.copytree(SAMPLE_GOOD_REPO, repo_path)

    def fake_create_temp_workspace(prefix: str = "drrepo-") -> Path:
        return tmp_path

    def fake_clone_public_github_repo(
        url: str, workspace_path: Path, timeout_seconds: int = 60
    ) -> Path:
        return repo_path

    def failing_cleanup(path: Path) -> None:
        raise PermissionError("Access is denied")

    monkeypatch.setattr(
        "drrepo.input.workspace.create_temp_workspace", fake_create_temp_workspace
    )
    monkeypatch.setattr(
        "drrepo.input.workspace.clone_public_github_repo",
        fake_clone_public_github_repo,
    )
    monkeypatch.setattr(
        "drrepo.input.workspace.cleanup_workspace", failing_cleanup
    )

    response = client.post(
        "/api/audits",
        json={
            "source_type": "github_url",
            "source_value": "https://github.com/owner/repo",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "audit" in data


def test_api_routes_not_swallowed_by_fallback(tmp_path: Path, monkeypatch):
    index = tmp_path / "index.html"
    index.write_text("<!doctype html><html><body>SPA</body></html>", encoding="utf-8")

    test_client = _make_client(monkeypatch, str(tmp_path))

    health = test_client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    profiles = test_client.get("/api/profiles")
    assert profiles.status_code == 200
    assert "profiles" in profiles.json()

    audit = test_client.post(
        "/api/audits",
        json={"source_type": "local_path", "source_value": SAMPLE_GOOD_REPO},
    )
    assert audit.status_code == 200
    assert "audit" in audit.json()


def _fake_advisor_package(
    status: str = "completed",
    source: str = "llm",
    provider: str = "gemini",
    grounding_valid: bool = True,
    fallback_reason: str | None = None,
) -> dict[str, object]:
    return {
        "advisor_service_version": "v1",
        "profile_id": "student_portfolio",
        "advisor_report": {"advisor_response": {"summary": "deterministic"}},
        "ai": {
            "requested": True,
            "status": status,
            "source": source,
            "provider": provider,
            "model": "gemini-2.5-flash" if provider == "gemini" else "deterministic-advisor",
            "advisor_response": {"summary": "AI summary"},
            "grounding_result": {
                "valid": grounding_valid,
                "checked_claims": 2,
                "validated_references": 2,
                "violations": [] if grounding_valid else ["unknown evidence reference: x"],
            },
            "fallback_reason": fallback_reason,
            "duration_ms": 100,
        },
    }


def _fake_api_audit() -> dict[str, object]:
    return {
        "path": "repo",
        "status": "ok",
        "metadata": {"total_files": 1, "python_files": 1},
        "scoring": {"overall_score": 72, "repository_health_score": 70, "categories": {}},
        "diagnosis": {
            "repository_health": {"label": "needs_attention", "score": 70, "summary": "Needs work."},
            "hard_flags": [],
            "limitations": [],
        },
        "project_understanding": {
            "project_identity": {
                "project_type": "web_service",
                "frameworks": ["fastapi"],
                "interfaces": ["rest_api"],
            },
            "entry_points": [{"path": "src/main.py", "symbol": "main"}],
        },
        "static_analysis": [
            {
                "tool": "ruff",
                "status": "completed",
                "findings": [
                    {"code": "RUF001", "message": "lint", "file_path": "src/main.py", "line": 12, "severity": "medium"}
                ],
            }
        ],
        "test_analysis": [
            {"tool": "pytest", "status": "completed", "summary": {"passed": 1, "failed": 0}, "findings": []},
            {"tool": "coverage", "status": "completed", "summary": {"coverage_percent": 65}, "findings": []},
        ],
        "repository_analysis": [],
        "devops_readiness": {"blockers": [{"id": "NO-CI", "title": "No CI configuration", "severity": "high"}]},
        "recommendations_v2": [{"id": "ADD-TESTS", "title": "Add tests", "priority": 1, "severity": "high"}],
        "remediation_suggestions": [
            {"code": "RUF001", "title": "Fix lint", "message": "lint", "severity": "medium", "tool": "ruff"}
        ],
        "remediation_summary": {},
    }


def _grounded_provider_response() -> dict[str, object]:
    return {
        "summary": "The overall score is 72.",
        "profile_context": "FastAPI web service.",
        "top_priorities": [
            {
                "title": "Fix lint",
                "why_it_matters": "RUF001 is present.",
                "evidence": ["RUF001", "src/main.py:12"],
                "suggested_fix": "Address the lint finding.",
                "priority": "high",
            }
        ],
        "lower_priority_items": [],
        "limitations": [],
        "next_steps": ["Run pytest."],
    }


def test_audit_ai_true_valid_grounded_response(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        "drrepo.api.service.build_advisor_for_audit",
        lambda *args, **kwargs: _fake_advisor_package(status="completed", source="llm", provider="gemini"),
    )
    response = client.post(
        "/api/audits",
        json={"source_type": "local_path", "source_value": str(tmp_path), "ai": True},
    )
    assert response.status_code == 200
    data = response.json()
    ai = data.get("ai_advisor") or {}
    assert ai.get("requested") is True
    assert ai.get("source") == "llm"
    assert ai.get("status") == "completed"
    assert ai.get("provider") == "gemini"
    assert ai.get("grounding_result", {}).get("valid") is True
    assert data.get("audit") is not None


def test_audit_ai_provider_unavailable_fallback(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        "drrepo.api.service.build_advisor_for_audit",
        lambda *args, **kwargs: _fake_advisor_package(
            status="provider_unavailable", source="deterministic", provider="deterministic_fallback", fallback_reason="Provider unavailable"
        ),
    )
    response = client.post(
        "/api/audits",
        json={"source_type": "local_path", "source_value": str(tmp_path), "ai": True},
    )
    assert response.status_code == 200
    data = response.json()
    ai = data.get("ai_advisor") or {}
    assert ai.get("source") == "deterministic"
    assert ai.get("status") == "provider_unavailable"
    assert ai.get("fallback_reason")


def test_audit_ai_timeout_fallback(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        "drrepo.api.service.build_advisor_for_audit",
        lambda *args, **kwargs: _fake_advisor_package(
            status="timeout", source="deterministic", provider="deterministic_fallback", fallback_reason="Provider timed out"
        ),
    )
    response = client.post(
        "/api/audits",
        json={"source_type": "local_path", "source_value": str(tmp_path), "ai": True},
    )
    assert response.status_code == 200
    data = response.json()
    ai = data.get("ai_advisor") or {}
    assert ai.get("status") == "timeout"
    assert data.get("status") == "ok"


def test_audit_ai_schema_invalid_fallback(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        "drrepo.api.service.build_advisor_for_audit",
        lambda *args, **kwargs: _fake_advisor_package(
            status="schema_invalid", source="deterministic", provider="deterministic_fallback", fallback_reason="Schema invalid"
        ),
    )
    response = client.post(
        "/api/audits",
        json={"source_type": "local_path", "source_value": str(tmp_path), "ai": True},
    )
    assert response.status_code == 200
    data = response.json()
    ai = data.get("ai_advisor") or {}
    assert ai.get("status") == "schema_invalid"


def test_audit_ai_grounding_rejection_fallback(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        "drrepo.api.service.build_advisor_for_audit",
        lambda *args, **kwargs: _fake_advisor_package(
            status="grounding_rejected",
            source="deterministic",
            provider="gemini",
            grounding_valid=False,
            fallback_reason="AI response contradicted the audit evidence",
        ),
    )
    response = client.post(
        "/api/audits",
        json={"source_type": "local_path", "source_value": str(tmp_path), "ai": True},
    )
    assert response.status_code == 200
    data = response.json()
    ai = data.get("ai_advisor") or {}
    assert ai.get("status") == "grounding_rejected"
    assert ai.get("source") == "deterministic"
    assert ai.get("grounding_result", {}).get("valid") is False


def test_audit_ai_internal_error_does_not_return_500(monkeypatch, tmp_path: Path):
    def boom(*args, **kwargs):
        raise RuntimeError("unexpected advisor failure")

    monkeypatch.setattr("drrepo.api.service.build_advisor_for_audit", boom)
    response = client.post(
        "/api/audits",
        json={"source_type": "local_path", "source_value": str(tmp_path), "ai": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ai_advisor"]["status"] == "internal_advisor_error"
    assert data["ai_advisor"]["source"] == "deterministic"
    assert data["audit"] is not None


def test_audit_builder_called_once_for_ai_success(monkeypatch, tmp_path: Path):
    calls: list[object] = []

    def tracking_build_audit(*args, **kwargs):
        calls.append(None)
        return _fake_api_audit()

    def fake_router(prompt_bundle, fallback_response, providers=None, provider_order=None):
        return {
            "selected_provider_id": "gemini",
            "used_fallback": False,
            "provider_attempts": [{"provider_id": "gemini", "status": "ok"}],
            "advisor_response": _grounded_provider_response(),
        }

    monkeypatch.setattr("drrepo.api.service.build_audit", tracking_build_audit)
    monkeypatch.setattr("drrepo.advisor.service.route_llm_advisor_response", fake_router)
    response = client.post(
        "/api/audits",
        json={"source_type": "local_path", "source_value": str(tmp_path), "ai": True},
    )
    assert response.status_code == 200
    assert len(calls) == 1
    assert response.json()["ai_advisor"]["status"] == "completed"


def test_audit_builder_called_once_for_ai_timeout_malformed_and_grounding_rejection(monkeypatch, tmp_path: Path):
    scenarios = [
        (
            "timeout",
            {
                "selected_provider_id": "deterministic_fallback",
                "used_fallback": True,
                "provider_attempts": [{"provider_id": "gemini", "status": "timeout", "error": "timeout"}],
                "advisor_response": _grounded_provider_response(),
            },
        ),
        (
            "invalid_json",
            {
                "selected_provider_id": "deterministic_fallback",
                "used_fallback": True,
                "provider_attempts": [{"provider_id": "gemini", "status": "invalid_json", "error": "malformed JSON"}],
                "advisor_response": _grounded_provider_response(),
            },
        ),
        (
            "grounding_rejected",
            {
                "selected_provider_id": "gemini",
                "used_fallback": False,
                "provider_attempts": [{"provider_id": "gemini", "status": "ok"}],
                "advisor_response": {**_grounded_provider_response(), "summary": "The overall score is 99."},
            },
        ),
    ]

    for expected_status, router_result in scenarios:
        calls: list[object] = []

        def tracking_build_audit(*args, **kwargs):
            calls.append(None)
            return _fake_api_audit()

        monkeypatch.setattr("drrepo.api.service.build_audit", tracking_build_audit)
        monkeypatch.setattr(
            "drrepo.advisor.service.route_llm_advisor_response",
            lambda prompt_bundle, fallback_response, providers=None, provider_order=None, result=router_result: result,
        )

        response = client.post(
            "/api/audits",
            json={"source_type": "local_path", "source_value": str(tmp_path), "ai": True},
        )

        assert response.status_code == 200
        assert len(calls) == 1
        ai = response.json()["ai_advisor"]
        assert ai["status"] == expected_status
        assert ai["source"] == "deterministic"
