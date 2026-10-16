"""OIDC JWT verification for requests to this service."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import httpx
import jwt
from jwt import InvalidTokenError

from app.config.settings import settings


class TokenValidationError(Exception):
    """A token could not be authenticated as an access token for this API."""


def _scopes(claims: dict[str, Any]) -> frozenset[str]:
    """Support standard OAuth `scope` and common `scp` access-token claims."""
    scope = claims.get("scope", "")
    values: list[str] = scope.split() if isinstance(scope, str) else []
    scp = claims.get("scp", [])
    if isinstance(scp, str):
        values.extend(scp.split())
    elif isinstance(scp, list):
        values.extend(item for item in scp if isinstance(item, str))
    return frozenset(values)


def roles(claims: dict[str, Any]) -> frozenset[str]:
    """Normalize the RWA application's `role` claim without trusting its type."""
    value = claims.get("role", [])
    if isinstance(value, str):
        return frozenset({value}) if value else frozenset()
    if isinstance(value, list):
        return frozenset(item for item in value if isinstance(item, str) and item)
    return frozenset()


@dataclass
class OIDCJWTVerifier:
    """Verify signed access tokens using a cached OIDC JWKS document."""

    issuer: str
    audience: str
    jwks_url: str
    jwt_secret: str | None = None
    cache_ttl_seconds: int = 300
    _jwks: dict[str, Any] | None = field(default=None, init=False)
    _expires_at: float = field(default=0, init=False)

    def _configured(self) -> bool:
        return bool(self.jwt_secret or (self.issuer and self.audience and self.jwks_url))

    async def _keys(self) -> dict[str, Any]:
        if self._jwks and time.monotonic() < self._expires_at:
            return self._jwks
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(self.jwks_url)
                response.raise_for_status()
                document = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise TokenValidationError("Unable to retrieve identity-provider signing keys.") from exc
        if not isinstance(document, dict) or not isinstance(document.get("keys"), list):
            raise TokenValidationError("Identity-provider signing keys are invalid.")
        self._jwks = document
        self._expires_at = time.monotonic() + self.cache_ttl_seconds
        return document

    async def verify(self, token: str) -> dict[str, Any]:
        if not self._configured():
            raise TokenValidationError("JWT authentication is not configured.")
        if self.jwt_secret:
            # The algorithm is fixed rather than read from the token header to
            # prevent algorithm-confusion attacks. Existing RWA tokens expose
            # `id` and `role`, so those are normalized by the dependency.
            try:
                claims = jwt.decode(
                    token,
                    self.jwt_secret,
                    algorithms=["HS256"],
                    options={"require": ["exp", "iat"]},
                )
            except InvalidTokenError as exc:
                raise TokenValidationError("Invalid or expired access token.") from exc
            if not isinstance(claims.get("id"), str) or not claims["id"].strip():
                raise TokenValidationError("Access token does not identify a user.")
            return claims
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            algorithm = header.get("alg")
        except InvalidTokenError as exc:
            raise TokenValidationError("Invalid access token.") from exc
        if algorithm not in {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"} or not isinstance(kid, str):
            raise TokenValidationError("Invalid access-token signing algorithm.")

        keys = await self._keys()
        matching_key = next((key for key in keys["keys"] if isinstance(key, dict) and key.get("kid") == kid), None)
        if matching_key is None:
            # Rotation may introduce a new key before the cache expires.
            self._jwks = None
            keys = await self._keys()
            matching_key = next((key for key in keys["keys"] if isinstance(key, dict) and key.get("kid") == kid), None)
        if matching_key is None:
            raise TokenValidationError("Unknown access-token signing key.")
        try:
            signing_key = jwt.PyJWK.from_dict(matching_key).key
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=[algorithm],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "sub"]},
            )
        except (InvalidTokenError, ValueError) as exc:
            raise TokenValidationError("Invalid or expired access token.") from exc
        if not isinstance(claims.get("sub"), str) or not claims["sub"].strip():
            raise TokenValidationError("Access token does not identify a user.")
        return claims


verifier = OIDCJWTVerifier(
    issuer=settings.auth_jwt_issuer,
    audience=settings.auth_jwt_audience,
    jwks_url=settings.auth_jwks_url,
    jwt_secret=settings.jwt_secret.get_secret_value() if settings.jwt_secret else None,
)
