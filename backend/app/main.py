from fastapi import FastAPI

from app.api.health import router as health_router
from app.webhooks.razorpay import router as razorpay_webhook_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="RecoverIQ API",
        description="Autonomous AI Revenue Recovery Agent",
        version="0.1.0",
    )

    application.include_router(health_router)
    application.include_router(razorpay_webhook_router)

    return application


app = create_app()
