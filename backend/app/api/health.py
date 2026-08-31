from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.core.security import AuthenticatedUser, require_viewer
from app.workers.telemetry import worker_telemetry

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Public service liveness check endpoint."""
    return {
        "status": "ok",
        "service": "recoveriq-api",
    }


@router.get("/health/worker")
async def worker_health_check(
    current_user: Annotated[AuthenticatedUser, Depends(require_viewer)],
) -> dict[str, Any]:
    """Authenticated worker health check and telemetry metrics endpoint."""
    return {
        "status": "ok",
        "service": "recoveriq-worker",
        "metrics": worker_telemetry.to_dict(),
    }
