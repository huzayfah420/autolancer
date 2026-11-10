"""Row 2: simulator connection status and operations (UC-001 steps 2-3, A1, E2, FR-002)."""

import httpx

from app.main import app
from app.marketplace import get_marketplace
from tests.conftest import POLICY, broken_marketplace


def test_starts_disconnected(client, owner_a):
    conn = client.get("/connections", headers=owner_a).json()[0]
    assert conn["status"] == "disconnected" and conn["enabled"] is False and conn["operations"] == []


def test_connect_shows_status_and_operations(client, owner_a):
    conn = client.put("/connections/simulator", json={"enabled": True}, headers=owner_a).json()
    assert conn["status"] == "connected"
    assert conn["operations"] == ["list_listings"]
    assert conn["account_name"] == "simulated-owner"
    assert "simulated" in conn["status_detail"]


def test_failed_capabilities_call_marks_unavailable(client, owner_a):
    def down(request):
        raise httpx.ConnectError("refused")

    app.dependency_overrides[get_marketplace] = lambda: broken_marketplace(down)
    conn = client.put("/connections/simulator", json={"enabled": True}, headers=owner_a).json()
    assert conn["status"] == "unavailable"
    assert conn["operations"] == []
    assert "unreachable" in conn["status_detail"]


def test_insufficient_capability_marks_unavailable(client, owner_a):
    caps = {"name": "Other market", "account": "x", "simulated": True, "operations": ["send_message"]}
    app.dependency_overrides[get_marketplace] = lambda: broken_marketplace(lambda req: httpx.Response(200, json=caps))
    conn = client.put("/connections/simulator", json={"enabled": True}, headers=owner_a).json()
    assert conn["status"] == "unavailable"
    assert "list_listings" in conn["status_detail"]


def test_toggle_off_leaves_it_disconnected_and_blocks_use(client, owner_a):
    client.put("/connections/simulator", json={"enabled": True}, headers=owner_a)
    client.post("/policy", json=POLICY, headers=owner_a)
    conn = client.put("/connections/simulator", json={"enabled": False}, headers=owner_a).json()
    assert conn["status"] == "disconnected" and conn["operations"] == []

    # FR-002 AC-2: using an unavailable operation stops with a reconnect instruction.
    r = client.post("/jobs/fetch", headers=owner_a)
    assert r.status_code == 409
    assert "Connect it on the Connections page" in r.json()["detail"]


def test_simulator_capabilities_endpoint(client):
    r = client.get("/sim/capabilities")
    assert r.status_code == 200 and r.json()["simulated"] is True
