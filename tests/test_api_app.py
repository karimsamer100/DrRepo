from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from drrepo.api.app import app

client = TestClient(app)

SAMPLE_GOOD_REPO = str(Path(__file__).resolve().parent.parent / "examples" / "sample_good_repo")


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
            "source_type": "github_url",
            "source_value": "https://github.com/owner/repo",
        },
    )
    assert response.status_code == 422


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
