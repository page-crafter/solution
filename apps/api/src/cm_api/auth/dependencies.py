import logging
from typing import Annotated, Any

import jwt
from cm_shared.settings.app import get_settings
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from cm_api.auth.user import CurrentUser

bearer = HTTPBearer(auto_error=True)
logger = logging.getLogger(__name__)


def decode_token(token: str) -> dict[str, Any]:
    """Validate a Keycloak JWT and return its claims."""
    settings = get_settings()
    jwks_client = PyJWKClient(settings.jwks_url)
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.keycloak_audience,
        issuer=settings.issuer_url,
        options={"verify_aud": True},
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> CurrentUser:
    """Return the authenticated user or raise an HTTP 401 error."""
    try:
        claims = decode_token(credentials.credentials)
    except jwt.InvalidTokenError as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid authentication token") from exc
    except Exception as exc:
        logger.error("Unexpected auth error: %s", exc, exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid authentication token") from exc

    roles = frozenset(claims.get("roles", []))
    return CurrentUser(
        subject=str(claims.get("sub", "")),
        email=str(claims.get("email", "")),
        display_name=str(claims.get("name") or claims.get("preferred_username") or "User"),
        roles=roles,
    )


def _require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if "admin" not in user.roles:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


require_admin = Depends(_require_admin)
