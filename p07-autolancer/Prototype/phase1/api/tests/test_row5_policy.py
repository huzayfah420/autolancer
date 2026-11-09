"""Row 5: versioned autonomy policy; invalid values rejected (UC-001 steps 6-7, E3, FR-004)."""

import pytest

from tests.conftest import POLICY


def test_each_save_creates_a_new_active_version(client, owner_a):
    assert client.get("/policy", headers=owner_a).json() == {"active": None, "history": []}
    v1 = client.post("/policy", json=POLICY, headers=owner_a).json()
    v2 = client.post("/policy", json={**POLICY, "max_bid": 1500}, headers=owner_a).json()
    assert (v1["version"], v2["version"]) == (1, 2)

    body = client.get("/policy", headers=owner_a).json()
    assert body["active"]["version"] == 2 and body["active"]["max_bid"] == 1500
    assert [p["version"] for p in body["history"]] == [2, 1]
    assert body["history"][1]["max_bid"] == 3000  # older version stays inspectable


def test_values_are_normalised(client, owner_a):
    p = client.post(
        "/policy", json={**POLICY, "excluded_keywords": [" Crypto ", "crypto", "NFT"], "allowed_actions": ["assess_jobs", "assess_jobs"]},
        headers=owner_a,
    ).json()
    assert p["excluded_keywords"] == ["crypto", "nft"]
    assert p["allowed_actions"] == ["assess_jobs"]


@pytest.mark.parametrize(
    "change",
    [
        {"max_bid": 0},
        {"max_bid": -10},
        {"daily_proposal_limit": -1},
        {"daily_proposal_limit": 1000},
        {"workload_limit": 99},
        {"daily_ai_cap_usd": -0.01},
        {"daily_ai_cap_usd": 500},
        {"min_job_budget": -1},
        {"allowed_actions": ["delete_everything"]},
        {"review_conditions": ["never"]},
        {"excluded_keywords": ["  "]},
        {"max_bid": "lots"},
        {"unexpected_field": True},
    ],
)
def test_invalid_policy_is_rejected_and_not_saved(client, owner_a, change):
    client.post("/policy", json=POLICY, headers=owner_a)
    r = client.post("/policy", json={**POLICY, **change}, headers=owner_a)
    assert r.status_code == 422
    body = client.get("/policy", headers=owner_a).json()
    assert body["active"]["version"] == 1 and len(body["history"]) == 1  # previous policy still active
