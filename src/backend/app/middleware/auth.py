"""Authentication middleware for local JWT and Azure AD token validation."""
import logging
import uuid
import httpx
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.models.auth import Role, UserRole
from app.services.user_service import UserService
from app.services.auth_service import AuthService


@dataclass
class AnonymousUser:
    """Anonymous user placeholder for unauthenticated requests.

    This is a simple dataclass that mimics the User model's key attributes
    but is not persisted to the database.
    """
    id: uuid.UUID
    email: str
    display_name: str
    oauth_provider: str
    oauth_id: str
    native_language: str
    timezone: str
    is_anonymous: bool = True

logger = logging.getLogger(__name__)
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def get_azure_jwks():
    """Fetch Azure AD public keys for token validation.

    We use the 'common' endpoint which includes keys for both v1 and v2 tokens.
    """
    # Use common keys endpoint - works for both v1 and v2 tokens
    jwks_url = "https://login.microsoftonline.com/common/discovery/keys"
    response = httpx.get(jwks_url)
    response.raise_for_status()
    return response.json()


def decode_token(token: str) -> dict:
    """Decode and validate Azure AD JWT token.

    Note: For SPA apps using openid/profile/email scopes, MSAL returns access tokens
    with audience='https://graph.microsoft.com'. We accept both the Graph audience
    and our client ID to support both access tokens and ID tokens.
    """
    settings = get_settings()
    jwks = get_azure_jwks()

    # Get the key ID from token header
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    # Find matching key
    rsa_key = None
    for key in jwks["keys"]:
        if key["kid"] == kid:
            rsa_key = key
            break

    if not rsa_key:
        raise JWTError("Unable to find matching key")

    # ID tokens always have our app's client ID as audience
    # Decode and validate
    payload = jwt.decode(
        token,
        rsa_key,
        algorithms=["RS256"],
        audience=settings.azure_ad_client_id,
        issuer=f"https://login.microsoftonline.com/{settings.azure_ad_tenant_id}/v2.0",
    )
    return payload


def decode_local_jwt(token: str) -> dict | None:
    """Try to decode a local JWT token.

    Returns the payload if valid, None if not a local JWT.
    """
    settings = get_settings()

    try:
        auth_service = AuthService()
        payload = auth_service.decode_access_token(token)
        return payload
    except JWTError:
        return None


async def verify_token(token: str) -> tuple[dict, str]:
    """Verify token and return claims with provider type.

    Returns: (claims_dict, provider) where provider is "local" or "azure_ad"
    """
    settings = get_settings()

    # Try local JWT first (if auth_mode allows)
    if settings.auth_mode in ["local", "both"]:
        local_claims = decode_local_jwt(token)
        if local_claims:
            return local_claims, "local"

    # Try Azure AD (if auth_mode allows)
    if settings.auth_mode in ["azure_ad", "both"]:
        try:
            azure_claims = decode_token(token)
            return azure_claims, "azure_ad"
        except Exception as e:
            logger.debug(f"Azure AD token validation failed: {type(e).__name__}")

    # Neither worked
    logger.warning("Token validation failed for all providers")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Dependency to get current authenticated user."""
    claims, provider = await verify_token(credentials.credentials)

    if provider == "local":
        # Local JWT: sub is user_id
        user_id = uuid.UUID(claims["sub"])
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        return user
    else:
        # Azure AD
        service = UserService(db)
        user = await service.get_or_create_user(
            oauth_provider="microsoft",
            oauth_id=claims["oid"],
            email=claims.get("preferred_username", claims.get("email", "")),
            display_name=claims.get("name"),
        )
        return user


# Type alias for use in route dependencies
CurrentUser = Annotated[User, Depends(get_current_user)]


# Anonymous user singleton
ANONYMOUS_USER = AnonymousUser(
    id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
    email="",
    display_name="Student Learner",
    oauth_provider="anonymous",
    oauth_id="anonymous",
    native_language="es",
    timezone="America/Los_Angeles",
    is_anonymous=True,
)


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(optional_security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Union[User, AnonymousUser]:
    """Return authenticated user or anonymous placeholder.

    Used for routes that should be accessible to both authenticated
    and unauthenticated users (e.g., browsing lessons).
    """
    if not credentials:
        return ANONYMOUS_USER

    try:
        claims = decode_token(credentials.credentials)
        service = UserService(db)
        return await service.get_or_create_user(
            oauth_provider="microsoft",
            oauth_id=claims["oid"],
            email=claims.get("preferred_username", claims.get("email", "")),
            display_name=claims.get("name"),
        )
    except JWTError as e:
        # Token validation failed (invalid signature, expired, malformed)
        logger.debug("JWT validation failed: %s", e)
        return ANONYMOUS_USER
    except KeyError as e:
        # Required claim missing from token
        logger.debug("Missing required claim in token: %s", e)
        return ANONYMOUS_USER


# Type alias for optional authentication
OptionalUser = Annotated[Union[User, AnonymousUser], Depends(get_optional_user)]


async def get_user_roles(user: User, db: AsyncSession) -> list[str]:
    """Get list of role names for a user."""
    stmt = (
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    result = await db.execute(stmt)
    return [r[0] for r in result.all()]


async def require_admin(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Dependency that requires the current user to have admin role."""
    roles = await get_user_roles(current_user, db)

    if "admin" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    return current_user


# Type alias for admin-only routes
AdminUser = Annotated[User, Depends(require_admin)]
