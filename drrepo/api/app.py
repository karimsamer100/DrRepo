from __future__ import annotations

import mimetypes
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from drrepo.advisor.profiles import list_profiles
from drrepo.advisor.llm_providers import get_supported_provider_ids
from drrepo.api.schemas import (
    AuditRequest,
    AuditResponse,
    CapabilitiesResponse,
    HealthCheckResponse,
    ProfileInfo,
    ProfilesResponse,
)
from drrepo.api.local_paths import local_path_policy
from drrepo.api.service import run_audit_service
from drrepo.analyzers.registry import capability_payload

# Ensure common static assets are served with correct MIME types even on
# systems where the registry / mime.types file is incomplete.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")


class SPAStaticFiles(StaticFiles):
    """StaticFiles subclass that falls back to index.html for non-asset paths.

    This preserves the standard SPA behavior: API routes are registered first
    and take precedence, while any browser route that does not map to a real
    file (and has no file extension) is served the root index.html.
    """

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and self.html and not Path(path).suffix:
                return await super().get_response("index.html", scope)
            raise

def _ai_advisor_capabilities() -> dict[str, object]:
    provider_routes: list[str] = []
    configured_providers: list[str] = []
    for provider_id in get_supported_provider_ids():
        if provider_id == "deterministic_fallback":
            continue
        provider_routes.append(provider_id)
        env_key = f"{provider_id.upper()}_API_KEY"
        if os.getenv(env_key):
            configured_providers.append(provider_id)
        # Gemini also accepts GOOGLE_API_KEY
        if provider_id == "gemini" and os.getenv("GOOGLE_API_KEY"):
            if provider_id not in configured_providers:
                configured_providers.append(provider_id)

    return {
        "supported": True,
        "provider_routes": provider_routes,
        "provider_configured": len(configured_providers) > 0,
        "configured_providers": configured_providers,
        "deterministic_fallback_available": True,
        "explicit_opt_in_required": True,
        "privacy_note": "AI advisor sends a bounded, redacted summary of audit evidence to a configured third-party provider only when explicitly requested.",
    }


app = FastAPI(title="DrRepo API", version="0.1.0")

_origins_env = os.getenv("DRREPO_API_CORS_ORIGINS", "")
allow_origins = [
    o.strip()
    for o in _origins_env.split(",")
    if o.strip()
] or ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

@app.get("/health", response_model=HealthCheckResponse)
async def health():
    return HealthCheckResponse(status="ok", version="0.1.0")


@app.get("/api/profiles", response_model=ProfilesResponse)
async def profiles():
    raw = list_profiles()
    return ProfilesResponse(
        profiles=[
            ProfileInfo(
                profile_id=p["profile_id"],
                display_name=p["display_name"],
                description=p["description"],
            )
            for p in raw
        ]
    )


@app.get("/api/capabilities", response_model=CapabilitiesResponse)
async def capabilities():
    payload = capability_payload()
    payload["ai_advisor"] = _ai_advisor_capabilities()
    payload["local_path"] = local_path_policy()
    return CapabilitiesResponse(**payload)


@app.post("/api/audits", response_model=AuditResponse)
async def audits(request: AuditRequest):
    try:
        result = run_audit_service(
            source_type=request.source_type,
            source_value=request.source_value,
            profile_id=request.profile_id,
            ai=request.ai,
            include_markdown=request.include_markdown,
            analysis_mode=request.analysis_mode,
            isolated_options=request.isolated_options.model_dump() if request.isolated_options else None,
        )
        return AuditResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotADirectoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


_default_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
_frontend_dist_env = os.getenv("DRREPO_FRONTEND_DIST", str(_default_frontend_dist))
frontend_dist = Path(_frontend_dist_env) if _frontend_dist_env else None

if frontend_dist and frontend_dist.is_dir():
    app.mount("/", SPAStaticFiles(directory=frontend_dist, html=True), name="frontend")
else:

    @app.get("/")
    async def root_frontend_missing():
        return {
            "message": "Frontend build not found. Run cd frontend && npm run build."
        }
