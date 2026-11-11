"""Fixes made after the browser walkthrough of UC-001 and UC-002."""

import httpx

from app.main import app
from app.marketplace import get_marketplace
from tests.conftest import POLICY, broken_marketplace


def test_unavailable_connection_is_reported_as_unavailable_not_disconnected(client, owner_a):
    def down(request):
        raise httpx.ConnectError("refused")

    app.dependency_overrides[get_marketplace] = lambda: broken_marketplace(down)
    client.put("/connections/simulator", json={"enabled": True}, headers=owner_a)
    client.post("/policy", json=POLICY, headers=owner_a)

    feed = client.get("/jobs", headers=owner_a).json()
    assert feed["connected"] is False and feed["connection_status"] == "unavailable"
    r = client.post("/jobs/fetch", headers=owner_a)
    assert r.status_code == 409 and "unavailable" in r.json()["detail"]


def test_feed_reports_connection_status(client, owner_a, ready_a):
    assert client.get("/jobs", headers=ready_a).json()["connection_status"] == "connected"


def test_removed_listing_shows_as_closed_after_the_next_fetch(client, ready_a):
    assert client.post("/sim/chaos/remove-listing/SIM-1001").status_code == 200
    assert client.post("/sim/chaos/remove-listing/SIM-1001").status_code == 404
    assert client.post("/jobs/fetch", headers=ready_a).json()["fetch"]["closed"] == 1
    items = client.get("/jobs", headers=ready_a).json()["items"]
    closed = [j for j in items if j["is_closed"]]
    assert [j["source_id"] for j in closed] == ["SIM-1001"] and items[-1]["source_id"] == "SIM-1001"
    assert not closed[0]["pursue_eligible"]


def test_mock_return_text_matches_the_ranking_basis(client, ready_a):
    job = client.get("/jobs", headers=ready_a).json()["items"][0]
    d = client.get(f"/jobs/{job['id']}", headers=ready_a).json()
    rate = d["score_breakdown"]["expected_return"]["hourly_rate"]
    assert f"About ${rate:.0f}/hour" in d["ai_output"]["expected_return_basis"]
