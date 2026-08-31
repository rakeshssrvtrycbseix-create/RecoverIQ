from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401
from app.api.auth import router as auth_router
from app.api.compliance import router as compliance_router
from app.api.data_governance import router as data_governance_router
from app.api.finops import router as finops_router
from app.api.health import router as health_router
from app.api.ml_governance import router as ml_governance_router
from app.api.observability import router as observability_router
from app.api.performance import router as performance_router
from app.api.recovery import router as recovery_router
from app.api.release_governance import router as release_governance_router
from app.api.resilience import router as resilience_router
from app.api.security import router as security_router
from app.api.zero_trust_security import router as zero_trust_security_router
from app.core.config import get_settings
from app.core.database import Base, get_engine
from app.core.security_headers import SecurityHeadersMiddleware
from app.webhooks.razorpay import router as razorpay_webhook_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application with security hardening."""
    settings = get_settings()
    application = FastAPI(
        title="RecoverIQ API",
        description="Autonomous AI Revenue Recovery Agent — Enterprise Hardened",
        version="0.1.0",
    )

    # 1. Initialize Tables
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass

    # 2. Security Headers Middleware
    application.add_middleware(SecurityHeadersMiddleware)

    # 3. Hardened CORS Configuration
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins
        if settings.cors_allowed_origins
        else ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # 4. Register Routers
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(recovery_router)
    application.include_router(security_router)
    application.include_router(compliance_router)
    application.include_router(resilience_router)
    application.include_router(observability_router)
    application.include_router(data_governance_router)
    application.include_router(performance_router)
    application.include_router(release_governance_router)
    application.include_router(zero_trust_security_router)
    application.include_router(finops_router)
    application.include_router(ml_governance_router)
    application.include_router(razorpay_webhook_router)

    return application


app = create_app()
