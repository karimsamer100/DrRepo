from __future__ import annotations

import importlib
import os
import shutil
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


def test_audit_local_path_success():
    response = client.post(
        "/api/audits",
        json={"source_type": "local_path", "source_value": SAMPLE_GOOD_REPO},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["source_type"] == "local_path"
    assert data["profile_id"] == "student_portfolio"
    assert "audit" in data
    assert "advisor" in data
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
    assert data["source_value"] == "https://github.com/owner/repo"
    assert "audit" in data


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


def test_audit_ai_not_supported(tmp_path: Path):
    response = client.post(
        "/api/audits",
        json={
            "source_type": "local_path",
            "source_value": str(tmp_path),
            "ai": True,
        },
    )
    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "ai" in detail or "not supported" in detail


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
