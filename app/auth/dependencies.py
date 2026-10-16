from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.api.dependencies.auth import get_investor_token
from app.auth.models import (
    AuthContext,
    AuthenticatedUser,
)
from app.auth.jwt import TokenValidationError, _scopes, roles, verifier


async def get_auth_context(
    token: str = Depends(get_investor_token),
) -> AuthContext:

    try:
        claims = await verifier.verify(token)
    except TokenValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return AuthContext(
        user=AuthenticatedUser(
            user_id=claims.get("sub") or claims.get("id"),
            scopes=_scopes(claims),
            roles=roles(claims),
            issuer=claims.get("iss", "rwa-local-jwt"),
        ),
        token=token,
    )


def require_scopes(*required_scopes: str) -> Callable:
    """FastAPI dependency that enforces all supplied OAuth scopes."""
    async def dependency(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
        missing = set(required_scopes) - auth.user.scopes
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this action.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return auth
    return dependency


def require_roles(*allowed_roles: str) -> Callable:
    """FastAPI dependency requiring at least one approved application role."""
    allowed = frozenset(role for role in allowed_roles if role)

    async def dependency(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if not allowed or not auth.user.roles.intersection(allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this action.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return auth
    return dependency
