from dataclasses import dataclass


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    scopes: frozenset[str]
    roles: frozenset[str]
    issuer: str

@dataclass(frozen=True)
class AuthContext:
    user: AuthenticatedUser
    token: str
