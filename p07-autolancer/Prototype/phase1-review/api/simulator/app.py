"""Marketplace Simulator sub-app.

Serves made-up listings from jobs.json and a few "chaos" endpoints for testing failure
and change handling. State lives in memory and resets when the process restarts.
The API never imports this module's state: it calls these endpoints over HTTP.
"""

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import os

from fastapi import Depends, FastAPI, Header, HTTPException, Query

DATA_FILE = Path(__file__).with_name("jobs.json")

# Extra listings handed out one by one by POST /chaos/add-listing.
EXTRA_LISTINGS = [
    {
        "title": "Monthly management accounts pack for a coffee roaster",
        "description": "We need a repeatable monthly management accounts pack in Excel: P&L vs budget, gross margin by product line, cash position and a one-page commentary. Xero export will be provided. First pack due within the deadline, then monthly.",
        "category": "finance", "budget_min": 600, "budget_max": 1100, "deadline_days": 10,
        "skills": ["excel", "management accounts", "xero", "financial reporting"],
    },
    {
        "title": "Fix failing CI pipeline for a Django project",
        "description": "Our GitHub Actions pipeline broke after upgrading to Python 3.13. Tests pass locally but fail in CI on a Postgres service container. Need diagnosis, a fix, and a short write-up of the cause.",
        "category": "software", "budget_min": 200, "budget_max": 400, "deadline_days": 3,
        "skills": ["python", "django", "github actions", "postgres"],
    },
    {
        "title": "Survey data cleaning and summary tables",
        "description": "Clean a 4,000-row customer survey export (duplicates, free-text country names, inconsistent dates) and produce summary tables and three charts in a Jupyter notebook with clear commentary.",
        "category": "data", "budget_min": 250, "budget_max": 450, "deadline_days": 6,
        "skills": ["python", "pandas", "data cleaning", "jupyter"],
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load() -> list[dict]:
    return json.loads(DATA_FILE.read_text())


# In-memory state.
state: dict = {}


def reset_state() -> None:
    """Restore the original listings and clear chaos flags (used by tests)."""
    state.clear()
    state.update({"listings": _load(), "fail_fetches": 0, "extra_index": 0})


reset_state()

sim = FastAPI(title="Autolancer Marketplace Simulator", version="1.0")


def chaos_guard(x_sim_token: str | None = Header(default=None)) -> None:
    """Chaos endpoints change what every owner sees, so a deployment can lock them."""
    expected = os.environ.get("SIMULATOR_CHAOS_TOKEN", "")
    if expected and x_sim_token != expected:
        raise HTTPException(403, "Chaos endpoints are locked")


@sim.get("/capabilities")
async def capabilities():
    """What this marketplace account can do. Phase 1 only needs list_listings."""
    return {"name": "Marketplace Simulator", "account": "simulated-owner", "simulated": True, "operations": ["list_listings"]}


@sim.get("/listings")
async def listings():
    if state["fail_fetches"] > 0:
        state["fail_fetches"] -= 1
        raise HTTPException(503, "Simulated marketplace outage")
    return {"listings": state["listings"], "generated_at": _now()}


@sim.post("/chaos/fail-next-fetch", dependencies=[Depends(chaos_guard)])
async def fail_next_fetch(count: int = Query(default=1, ge=1, le=10)):
    """The next `count` GET /listings calls return 503. The API retries up to 3 times per
    fetch, so count=1 shows a recovered retry and count=3 fails the whole fetch."""
    state["fail_fetches"] = count
    return {"failing_fetches": count}


@sim.post("/chaos/edit-listing/{listing_id}", dependencies=[Depends(chaos_guard)])
async def edit_listing(listing_id: str):
    """Change a listing's budget and description, as a client edit would."""
    for item in state["listings"]:
        if item["id"] == listing_id:
            item["budget_max"] = round(item["budget_max"] * 1.2)
            item["description"] += " Update: the client now also wants a short summary report."
            item["updated_at"] = _now()
            return item
    raise HTTPException(404, "Listing not found")


@sim.post("/chaos/add-listing", status_code=201, dependencies=[Depends(chaos_guard)])
async def add_listing():
    """Post a brand-new listing (cycles through EXTRA_LISTINGS)."""
    i = state["extra_index"]
    state["extra_index"] += 1
    item = copy.deepcopy(EXTRA_LISTINGS[i % len(EXTRA_LISTINGS)])
    item.update(
        id=f"SIM-{2001 + i}",
        currency="USD",
        client={"name": f"New Client {i + 1}", "country": "GB", "rating": 4.6},
        url=f"https://marketplace.example/jobs/SIM-{2001 + i}",
        posted_at=_now(),
        updated_at=_now(),
    )
    state["listings"].append(item)
    return item
