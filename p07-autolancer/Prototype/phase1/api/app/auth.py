"""Supabase JWT verification. Every protected endpoint depends on `current_owner`.

Supports both Supabase signing modes:
- legacy HS256 shared secret (SUPABASE_JWT_SECRET), and
- asymmetric keys published at {SUPABASE_URL}/auth/v1/.well-known/jwks.json.
Any failure returns the same generic 401, so nothing about the account leaks (UC-001 E1).
"""

import uuid
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings

bearer = HTTPBearer(auto_error=False)


@dataclass
class Owner:
    id: uuid.UUID
    email: str | None


@lru_cache
def _jwks_client(supabase_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json")


def decode_token(token: str) -> dict:
    settings = get_settings()
    if settings.supabase_jwt_secret:
        return jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"], audience="authenticated")
    if not settings.supabase_url:
        raise jwt.InvalidTokenError("No verification key configured")
    key = _jwks_client(settings.supabase_url).get_signing_key_from_jwt(token)
    return jwt.decode(token, key.key, algorithms=["ES256", "RS256"], audience="authenticated")


def current_owner(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Owner:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    if creds is None:
        raise unauthorized
    try:
        claims = decode_token(creds.credentials)
        return Owner(id=uuid.UUID(claims["sub"]), email=claims.get("email"))
    except Exception:  # bad signature, expired, wrong audience, missing sub, JWKS down...
        raise unauthorized
