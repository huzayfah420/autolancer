"""Local stand-in for Supabase Auth, for running the prototype with no Supabase project.

LOCAL DEVELOPMENT ONLY. Never deploy this: it holds plain-text demo passwords.

It answers the few GoTrue endpoints the hub's supabase-js client calls for email/password
sign-in and signs HS256 tokens with SUPABASE_JWT_SECRET, which the API then verifies in
its "legacy secret" mode. Run from the api/ directory so the same virtualenv is used:

    SUPABASE_JWT_SECRET=<same value as api/.env> \
        .venv/bin/uvicorn local_auth:app --app-dir ../dev --port 9999

and point the hub at it with NEXT_PUBLIC_SUPABASE_URL=http://localhost:9999.
Accounts come from LOCAL_AUTH_USERS ("email:password,email:password").
"""

import os
import secrets
import time
import uuid

import jwt
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

SECRET = os.environ["SUPABASE_JWT_SECRET"]
TOKEN_SECONDS = 3600

USERS = dict(
    pair.split(":", 1)
    for pair in os.environ.get("LOCAL_AUTH_USERS", "owner@example.com:owner-pass-123").split(",")
)
# refresh token -> email (in memory; restarting the stub signs everyone out)
refresh_tokens: dict[str, str] = {}

app = FastAPI(title="Local auth stub (dev only)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def user_json(email: str) -> dict:
    # A stable id per email, so an owner keeps their data across restarts.
    uid = str(uuid.uuid5(uuid.NAMESPACE_DNS, email))
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return {
        "id": uid, "aud": "authenticated", "role": "authenticated", "email": email,
        "email_confirmed_at": now, "app_metadata": {"provider": "email", "providers": ["email"]},
        "user_metadata": {}, "identities": [], "created_at": now, "updated_at": now,
    }


def session_json(email: str) -> dict:
    user = user_json(email)
    now = int(time.time())
    claims = {
        "sub": user["id"], "aud": "authenticated", "role": "authenticated", "email": email,
        "aal": "aal1", "iat": now, "exp": now + TOKEN_SECONDS, "session_id": str(uuid.uuid4()),
    }
    refresh = secrets.token_urlsafe(24)
    refresh_tokens[refresh] = email
    return {
        "access_token": jwt.encode(claims, SECRET, algorithm="HS256"), "token_type": "bearer",
        "expires_in": TOKEN_SECONDS, "expires_at": now + TOKEN_SECONDS, "refresh_token": refresh, "user": user,
    }


def invalid(message: str, code: str) -> JSONResponse:
    return JSONResponse({"code": 400, "error_code": code, "msg": message}, status_code=400)


@app.post("/auth/v1/token")
async def token(request: Request, grant_type: str = ""):
    body = await request.json()
    if grant_type == "password":
        email = str(body.get("email", "")).lower()
        expected = USERS.get(email)
        # Same answer for an unknown email and a wrong password.
        if expected is None or not secrets.compare_digest(expected, str(body.get("password", ""))):
            return invalid("Invalid login credentials", "invalid_credentials")
        return session_json(email)
    if grant_type == "refresh_token":
        email = refresh_tokens.pop(str(body.get("refresh_token", "")), None)
        if email is None:
            return invalid("Invalid Refresh Token", "refresh_token_not_found")
        return session_json(email)
    return invalid("Unsupported grant type", "invalid_request")


@app.get("/auth/v1/user")
def user(request: Request):
    try:
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        claims = jwt.decode(token, SECRET, algorithms=["HS256"], audience="authenticated")
        return user_json(claims["email"])
    except Exception:
        return JSONResponse({"code": 401, "error_code": "bad_jwt", "msg": "Invalid token"}, status_code=401)


@app.post("/auth/v1/logout")
def logout():
    return Response(status_code=204)
