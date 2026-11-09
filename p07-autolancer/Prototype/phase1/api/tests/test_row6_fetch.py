"""Row 6: fetch on demand, filter, store without duplicates, keep list on failure (UC-002 steps 1-2, E1, FR-005)."""

from sqlalchemy import func, select

from app.models import Listing
from tests.conftest import POLICY, setup_owner

FILTERED_OUT = {"SIM-1005", "SIM-1010", "SIM-1006"}  # crypto, gambling, budget below 200


def listing_count(session_factory) -> int:
    with session_factory() as db:
        return db.scalar(select(func.count()).select_from(Listing))


def test_fetch_requires_policy(client, owner_a):
    client.put("/connections/simulator", json={"enabled": True}, headers=owner_a)
    r = client.post("/jobs/fetch", headers=owner_a)
    assert r.status_code == 409 and "policy" in r.json()["detail"].lower()


def test_fetch_requires_discover_permission(client, owner_a):
    setup_owner(client, owner_a, policy={**POLICY, "allowed_actions": ["assess_jobs"]})
    r = client.post("/jobs/fetch", headers=owner_a)
    assert r.status_code == 409 and "discovery" in r.json()["detail"]


def test_fetch_applies_min_budget_and_excluded_keywords(client, owner_a):
    setup_owner(client, owner_a)
    result = client.post("/jobs/fetch", headers=owner_a).json()["fetch"]
    assert result["ok"] and result["new"] == 27 and result["filtered_out"] == 3
    ids = {j["source_id"] for j in client.get("/jobs", headers=owner_a).json()["items"]}
    assert len(ids) == 27 and not ids & FILTERED_OUT


def test_refetch_creates_no_duplicates(client, ready_a, session_factory):
    before = listing_count(session_factory)
    result = client.post("/jobs/fetch", headers=ready_a).json()["fetch"]
    assert result["new"] == 0 and result["changed"] == 0 and result["unchanged"] == 27
    assert listing_count(session_factory) == before == 27


def test_failed_fetch_keeps_list_and_last_updated(client, ready_a, session_factory):
    feed_before = client.get("/jobs", headers=ready_a).json()
    client.post("/sim/chaos/fail-next-fetch")

    r = client.post("/jobs/fetch", headers=ready_a).json()
    assert r["fetch"]["ok"] is False and "503" in r["fetch"]["error"]
    assert r["assessment"] is None  # cycle deferred

    feed_after = client.get("/jobs", headers=ready_a).json()
    assert len(feed_after["items"]) == len(feed_before["items"]) == 27
    assert feed_after["last_fetch_at"] == feed_before["last_fetch_at"]
    assert feed_after["last_fetch_error"] and "503" in feed_after["last_fetch_error"]

    # The next fetch succeeds and clears the error.
    assert client.post("/jobs/fetch", headers=ready_a).json()["fetch"]["ok"] is True
    assert client.get("/jobs", headers=ready_a).json()["last_fetch_error"] is None


def test_changed_and_added_listings(client, ready_a, session_factory):
    client.post("/sim/chaos/edit-listing/SIM-1001")
    client.post("/sim/chaos/add-listing")
    result = client.post("/jobs/fetch", headers=ready_a).json()["fetch"]
    assert (result["new"], result["changed"], result["unchanged"]) == (1, 1, 26)
    with session_factory() as db:
        edited = db.scalar(select(Listing).where(Listing.source_id == "SIM-1001"))
    assert edited.version == 2 and edited.budget_max == 3000
    assert listing_count(session_factory) == 28


def test_simulator_chaos_edit_unknown_listing(client):
    assert client.post("/sim/chaos/edit-listing/NOPE").status_code == 404
