import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.security import (
    AuthenticatedUser,
    LoginRequest,
    TokenResponse,
    create_access_token,
    get_current_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Issue signed JWT access token for operator or viewer",
)
def issue_access_token(payload: LoginRequest) -> TokenResponse:
    """Issue a cryptographically signed JWT access token with role claims."""
    settings = get_settings()
    token = create_access_token(
        user_id=payload.user_id,
        role=payload.role.value,
    )
    expires_in = settings.jwt_access_token_expire_minutes * 60

    logger.info(
        "auth_token_issued",
        extra={"user_id": payload.user_id, "role": payload.role.value},
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user_id=payload.user_id,
        role=payload.role.value,
    )


@router.get(
    "/me",
    response_model=AuthenticatedUser,
    summary="Get verified user identity and role from authentication token",
)
def get_current_user_profile(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    """Return verified caller identity and authorization role."""
    return current_user
