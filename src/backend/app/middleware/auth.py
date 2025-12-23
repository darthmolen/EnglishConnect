"""Authentication middleware for Azure AD token validation."""
import httpx
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.services.user_service import UserService

security = HTTPBearer()


@lru_cache(maxsize=1)
def get_azure_jwks():
    """Fetch Azure AD public keys for token validation."""
    settings = get_settings()
    jwks_url = f"https://login.microsoftonline.com/{settings.azure_ad_tenant_id}/discovery/v2.0/keys"
    response = httpx.get(jwks_url)
    response.raise_for_status()
    return response.json()


def decode_token(token: str) -> dict:
    """Decode and validate Azure AD JWT token."""
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

    # Decode and validate
    payload = jwt.decode(
        token,
        rsa_key,
        algorithms=["RS256"],
        audience=settings.azure_ad_client_id,
        issuer=f"https://login.microsoftonline.com/{settings.azure_ad_tenant_id}/v2.0",
    )
    return payload


async def verify_token(token: str) -> dict:
    """Verify token and return claims."""
    try:
        return decode_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Dependency to get current authenticated user."""
    claims = await verify_token(credentials.credentials)

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
