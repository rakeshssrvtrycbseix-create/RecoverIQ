from fastapi import APIRouter

from app.workers.telemetry import worker_telemetry

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "recoveriq-api",
    }


@router.get("/health/worker")
async def worker_health_check() -> dict:
    """Worker health check and telemetry metrics endpoint."""
    return {
        "status": "ok",
        "service": "recoveriq-worker",
        "metrics": worker_telemetry.to_dict(),
    }
