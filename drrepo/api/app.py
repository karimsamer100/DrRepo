from __future__ import annotations

from fastapi import FastAPI, HTTPException

from drrepo.advisor.profiles import list_profiles
from drrepo.api.schemas import (
    AuditRequest,
    AuditResponse,
    HealthCheckResponse,
    ProfileInfo,
    ProfilesResponse,
)
from drrepo.api.service import run_audit_service

app = FastAPI(title="DrRepo API", version="0.1.0")


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


@app.post("/api/audits", response_model=AuditResponse)
async def audits(request: AuditRequest):
    try:
        result = run_audit_service(
            source_value=request.source_value,
            profile_id=request.profile_id,
            ai=request.ai,
            include_markdown=request.include_markdown,
        )
        return AuditResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotADirectoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
