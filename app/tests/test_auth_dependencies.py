import pytest
import jwt
from fastapi import HTTPException

from app.auth.dependencies import get_auth_context, require_roles, require_scopes
from app.auth.jwt import OIDCJWTVerifier, TokenValidationError


@pytest.mark.asyncio
async def test_auth_context_uses_validated_subject_and_scopes(monkeypatch):
    async def verify(_: str):
        return {"id": "user-123", "role": "investor", "iss": "https://issuer.example", "scope": "rwa:chat portfolio:read"}

    monkeypatch.setattr("app.auth.dependencies.verifier.verify", verify)
    context = await get_auth_context("valid-token")

    assert context.user.user_id == "user-123"
    assert context.user.scopes == frozenset({"rwa:chat", "portfolio:read"})
    assert context.user.roles == frozenset({"investor"})


@pytest.mark.asyncio
async def test_auth_context_rejects_invalid_token(monkeypatch):
    async def verify(_: str):
        raise TokenValidationError("bad token")

    monkeypatch.setattr("app.auth.dependencies.verifier.verify", verify)
    with pytest.raises(HTTPException) as error:
        await get_auth_context("invalid-token")
    assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_scope_dependency_rejects_missing_scope(monkeypatch):
    async def verify(_: str):
        return {"sub": "user-123", "iss": "https://issuer.example", "scope": "portfolio:read"}

    monkeypatch.setattr("app.auth.dependencies.verifier.verify", verify)
    dependency = require_scopes("rwa:chat")
    context = await get_auth_context("valid-token")
    with pytest.raises(HTTPException) as error:
        await dependency(context)
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_role_dependency_allows_rwa_investor(monkeypatch):
    async def verify(_: str):
        return {"id": "user-123", "role": "investor", "iss": "rwa-local-jwt"}

    monkeypatch.setattr("app.auth.dependencies.verifier.verify", verify)
    dependency = require_roles("investor", "admin")
    context = await get_auth_context("valid-token")
    assert await dependency(context) == context


@pytest.mark.asyncio
async def test_hs256_rwa_token_is_verified_and_uses_id_claim():
    verifier = OIDCJWTVerifier("", "", "", jwt_secret="test-secret")
    token = jwt.encode(
        {"id": "user-123", "role": "investor", "iat": 1_700_000_000, "exp": 2_000_000_000},
        "test-secret",
        algorithm="HS256",
    )

    claims = await verifier.verify(token)

    assert claims["id"] == "user-123"
