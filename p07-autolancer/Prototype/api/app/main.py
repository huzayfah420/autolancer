"""FastAPI entry point: `uvicorn app.main:app`.

Creates tables on startup, mounts the Marketplace Simulator at /sim (one deploy) and
wires the routers. Run from the api/ directory.
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from simulator.app import sim

from . import models  # noqa: F401  (registers tables on Base.metadata)
from .auth import Owner, current_owner
from .config import get_settings
from .db import Base, engine
from .routers import connections, jobs, policy, profile
from .schemas import ALLOWED_ACTIONS, REVIEW_CONDITIONS, SERVICES


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)  # creates missing tables; never alters existing ones
    yield


app = FastAPI(title="Autolancer API (Phase 1)", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

for r in (connections.router, profile.router, policy.router, jobs.router):
    app.include_router(r)

# The simulator lives in the same process but the API still calls it over HTTP (SIMULATOR_URL).
app.mount("/sim", sim)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/me")
def me(owner: Owner = Depends(current_owner)):
    return {"owner_id": str(owner.id), "email": owner.email}


@app.get("/options")
def options():
    """Fixed choices for the hub's forms, so the API stays the single source of truth."""
    return {"services": SERVICES, "allowed_actions": ALLOWED_ACTIONS, "review_conditions": REVIEW_CONDITIONS}
