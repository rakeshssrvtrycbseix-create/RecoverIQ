import logging
import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated, Any

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Security scheme for FastAPI OpenAPI docs and header extraction
bearer_scheme = HTTPBearer(auto_error=False)


class UserRole(StrEnum):
    """Explicit Role-Based Access Control (RBAC) tiers."""

    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


ROLE_HIERARCHY: dict[str, int] = {
    UserRole.VIEWER.value: 1,
    UserRole.OPERATOR.value: 2,
    UserRole.ADMIN.value: 3,
}


def has_required_role(user_role: str, required_role: str) -> bool:
    """Check whether user_role meets or exceeds the required_role hierarchy level."""
    user_level = ROLE_HIERARCHY.get(user_role.lower(), 0)
    required_level = ROLE_HIERARCHY.get(required_role.lower(), 99)
    return user_level >= required_level


# In-memory revocation cache for instant revocation tripwires
_REVOKED_JTI_SET: set[str] = set()


def revoke_token_jti(jti: str) -> None:
    """Add a JWT ID (jti) to the active revocation blacklist."""
    if jti:
        _REVOKED_JTI_SET.add(jti)


def is_token_jti_revoked(jti: str | None) -> bool:
    """Check if a JWT ID is currently blacklisted/revoked."""
    if not jti:
        return False
    return jti in _REVOKED_JTI_SET


class AuthenticatedUser(BaseModel):
    """Verified user identity and authorization context extracted from credentials."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1, description="Verified user identifier")
    role: str = Field(default=UserRole.VIEWER.value, description="RBAC role")
    token_type: str = Field(default="bearer", description="bearer or api_key")
    jti: str | None = Field(default=None, description="Unique JWT Token ID")


class TokenResponse(BaseModel):
    """Token issuance payload."""

    model_config = ConfigDict(frozen=True)

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    role: str
    jti: str | None = None


class LoginRequest(BaseModel):
    """Demo login / token issuance request."""

    model_config = ConfigDict(frozen=True)

    user_id: str = Field(default="op_default", min_length=1, max_length=64)
    role: UserRole = Field(default=UserRole.OPERATOR)
    secret: str | None = Field(default=None)


def create_access_token(
    user_id: str,
    role: str = UserRole.VIEWER.value,
    expires_delta: timedelta | None = None,
    jti: str | None = None,
) -> str:
    """Generate a cryptographically signed HS256 JWT access token containing subject, role, and jti claims."""
    settings = get_settings()
    now_utc = datetime.now(UTC)
    expire_minutes = settings.jwt_access_token_expire_minutes
    expires_at = now_utc + (expires_delta or timedelta(minutes=expire_minutes))
    token_jti = jti or uuid.uuid4().hex

    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role.lower(),
        "jti": token_jti,
        "iat": int(now_utc.timestamp()),
        "nbf": int(now_utc.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": settings.app_name,
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token


def decode_access_token(token: str) -> AuthenticatedUser:
    """Decode and cryptographically verify a JWT access token with algorithm pinning and revocation check."""
    settings = get_settings()
    try:
        # Enforce strict algorithm verification against configured algorithm (e.g. HS256)
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.app_name,
            options={"require": ["exp", "iat", "sub"]},
        )
        user_id: str | None = payload.get("sub")
        role: str = payload.get("role", UserRole.VIEWER.value)
        jti: str | None = payload.get("jti")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload missing subject identifier (sub).",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if role not in ROLE_HIERARCHY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token contains unrecognized role '{role}'.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if token has been revoked
        if is_token_jti_revoked(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has been revoked.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return AuthenticatedUser(id=user_id, role=role, token_type="bearer", jti=jti)

    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user(
    auth_header: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> AuthenticatedUser:
    """
    Authoritative authentication dependency.
    Extracts, verifies, and returns the authenticated user identity and role.
    """
    settings = get_settings()

    # 1. Check API Key authentication (e.g. for machine/internal automation)
    if x_api_key and settings.admin_api_key and x_api_key == settings.admin_api_key:
        return AuthenticatedUser(
            id="api_key_admin",
            role=UserRole.ADMIN.value,
            token_type="api_key",
        )

    # 2. Check Bearer Token authentication
    if auth_header and auth_header.credentials:
        return decode_access_token(auth_header.credentials)

    # 3. No valid credentials provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide a valid Bearer token or API key.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(required_role: UserRole):
    """Factory creating an authorization dependency enforcing RBAC hierarchy."""

    def _role_checker(
        current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if not has_required_role(current_user.role, required_role.value):
            logger.warning(
                "unauthorized_rbac_access_attempt",
                extra={
                    "user_id": current_user.id,
                    "user_role": current_user.role,
                    "required_role": required_role.value,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. User '{current_user.id}' with role '{current_user.role}' "
                    f"does not have required permission '{required_role.value}'."
                ),
            )
        return current_user

    return _role_checker


# Convenient RBAC dependency shortcuts
require_viewer = require_role(UserRole.VIEWER)
require_operator = require_role(UserRole.OPERATOR)
require_admin = require_role(UserRole.ADMIN)
