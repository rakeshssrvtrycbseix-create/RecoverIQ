from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.api_route("/health", methods=["GET", "POST"])
async def health_check() -> dict:
    """Health check endpoint supporting both GET and POST requests."""
    return {
        "status": "ok",
        "service": "recoveriq-api",
    }
