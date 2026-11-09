"""Row 1: sign-in/out, generic auth failures, owners see only their own rows (UC-001 step 1, E1, FR-001)."""

import uuid

import pytest

from tests.conftest import make_token

PROTECTED = [("get", "/me"), ("get", "/profile"), ("get", "/policy"), ("get", "/connections"), ("get", "/jobs"), ("post", "/jobs/fetch")]


@pytest.mark.parametrize("method,path", PROTECTED)
def test_no_token_is_rejected(client, method, path):
    r = getattr(client, method)(path)
    assert r.status_code == 401
    assert r.json() == {"detail": "Not authenticated"}


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        make_token(str(uuid.uuid4()), secret="some-other-secret-that-is-32-bytes-long!!"),  # forged
        make_token(str(uuid.uuid4()), exp_offset=-60),  # expired
    ],
)
def test_bad_tokens_get_the_same_generic_error(client, token):
    r = client.get("/profile", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert r.json() == {"detail": "Not authenticated"}  # nothing about why, nothing about the account


def test_valid_token_identifies_owner(client, owner_a):
    r = client.get("/me", headers=owner_a)
    assert r.status_code == 200
    assert uuid.UUID(r.json()["owner_id"])


def test_owner_isolation(client, ready_a, owner_b):
    a_jobs = client.get("/jobs", headers=ready_a).json()["items"]
    assert a_jobs

    # Owner B sees none of A's data...
    assert client.get("/jobs", headers=owner_b).json()["items"] == []
    assert client.get("/policy", headers=owner_b).json() == {"active": None, "history": []}
    assert client.get("/profile", headers=owner_b).json()["services"] == []
    assert client.get("/connections", headers=owner_b).json()[0]["status"] == "disconnected"

    # ...and cannot read or act on A's job by id (same 404 as a missing job).
    job_id = a_jobs[0]["id"]
    assert client.get(f"/jobs/{job_id}", headers=owner_b).status_code == 404
    assert client.post(f"/jobs/{job_id}/assess", headers=owner_b).status_code == 404
    assert client.get(f"/jobs/{job_id}", headers=ready_a).status_code == 200


def test_owners_have_separate_listing_copies(client, ready_a, owner_b):
    from tests.conftest import setup_owner

    setup_owner(client, owner_b)
    client.post("/jobs/fetch", headers=owner_b)
    a_ids = {j["id"] for j in client.get("/jobs", headers=ready_a).json()["items"]}
    b_ids = {j["id"] for j in client.get("/jobs", headers=owner_b).json()["items"]}
    assert a_ids and b_ids and a_ids.isdisjoint(b_ids)
