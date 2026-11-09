"""Test fixtures: in-memory SQLite, HS256 test tokens, and the real simulator over HTTP.

The marketplace adapter is pointed at the mounted /sim app through Starlette's TestClient
(an httpx.Client), so tests exercise the same HTTP path the API uses in production.
"""

import os

# Must be set before the app is imported (settings are read once).
os.environ.update(
    DATABASE_URL="sqlite://",
    SUPABASE_JWT_SECRET="test-secret-that-is-at-least-32-bytes-long",
    SUPABASE_URL="",
    LLM_MODEL="mock",
    SIMULATOR_URL="http://testserver/sim",
)

import time
import uuid

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.marketplace import SimulatorAdapter, get_marketplace
from simulator.app import reset_state

PROFILE = {
    "services": ["finance", "software", "data"],
    "skills_summary": "Python, Excel, pandas, financial modelling, cash flow forecasting and dashboards.",
    "evidence": [
        {"kind": "link", "title": "Finance: 13-week cash-flow model", "content": "https://example.com/cashflow"},
        {"kind": "text", "title": "Software: FastAPI invoice service", "content": "Built a python fastapi and postgres API with docker."},
    ],
}

POLICY = {
    "allowed_actions": ["discover_jobs", "assess_jobs", "submit_proposals"],
    "max_bid": 3000,
    "daily_proposal_limit": 5,
    "workload_limit": 3,
    "daily_ai_cap_usd": 1.0,
    "review_conditions": [],
    "min_job_budget": 200,
    "excluded_keywords": ["crypto", "gambling"],
}


def make_token(owner_id: str, secret: str = "test-secret-that-is-at-least-32-bytes-long", exp_offset: int = 3600) -> str:
    claims = {"sub": owner_id, "aud": "authenticated", "email": f"{owner_id[:8]}@example.com", "exp": int(time.time()) + exp_offset}
    return jwt.encode(claims, secret, algorithm="HS256")


def auth(owner_id: str) -> dict:
    return {"Authorization": f"Bearer {make_token(owner_id)}"}


@pytest.fixture
def session_factory():
    # In-memory SQLite by default; set TEST_DATABASE_URL to run the suite against Postgres.
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        engine = create_engine(url)
        Base.metadata.drop_all(engine)
    else:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def client(session_factory):
    reset_state()

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    # The adapter talks HTTP to /sim on the same app, exactly as SIMULATOR_URL does in production.
    sim_http = TestClient(app, base_url="http://testserver/sim")
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_marketplace] = lambda: SimulatorAdapter(sim_http)
    yield TestClient(app)
    app.dependency_overrides.clear()


def broken_marketplace(handler) -> SimulatorAdapter:
    """An adapter whose HTTP calls are answered by `handler` (for outage/capability tests)."""
    return SimulatorAdapter(httpx.Client(base_url="http://down.test", transport=httpx.MockTransport(handler)))


@pytest.fixture
def owner_a() -> dict:
    return auth(str(uuid.uuid4()))


@pytest.fixture
def owner_b() -> dict:
    return auth(str(uuid.uuid4()))


def setup_owner(client: TestClient, headers: dict, policy: dict | None = None, profile: dict | None = None) -> None:
    """Connect the simulator, save a profile and a policy."""
    assert client.put("/connections/simulator", json={"enabled": True}, headers=headers).json()["status"] == "connected"
    assert client.put("/profile", json=profile or PROFILE, headers=headers).status_code == 200
    assert client.post("/policy", json=policy or POLICY, headers=headers).status_code == 201


@pytest.fixture
def ready_a(client, owner_a) -> dict:
    """Owner A, fully set up and with one completed fetch + assessment cycle."""
    setup_owner(client, owner_a)
    r = client.post("/jobs/fetch", headers=owner_a)
    assert r.status_code == 200, r.text
    return owner_a
