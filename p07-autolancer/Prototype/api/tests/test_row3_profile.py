"""Row 3: profile form with services, skills summary and evidence (UC-001 step 4, FR-003)."""

from tests.conftest import PROFILE


def test_new_owner_gets_empty_profile(client, owner_a):
    p = client.get("/profile", headers=owner_a).json()
    assert p["version"] == 1 and p["services"] == [] and p["evidence"] == []


def test_save_and_read_back(client, owner_a):
    saved = client.put("/profile", json=PROFILE, headers=owner_a).json()
    assert saved["version"] == 2
    read = client.get("/profile", headers=owner_a).json()
    assert read["services"] == ["data", "finance", "software"]
    assert read["skills_summary"] == PROFILE["skills_summary"]
    assert read["evidence"] == PROFILE["evidence"]


def test_version_only_changes_on_real_change(client, owner_a):
    client.put("/profile", json=PROFILE, headers=owner_a)
    assert client.put("/profile", json=PROFILE, headers=owner_a).json()["version"] == 2
    changed = {**PROFILE, "skills_summary": "Something else"}
    assert client.put("/profile", json=changed, headers=owner_a).json()["version"] == 3


def test_invalid_profile_is_rejected(client, owner_a):
    bad_service = {**PROFILE, "services": ["astrology"]}
    bad_link = {**PROFILE, "evidence": [{"kind": "link", "title": "x", "content": "not a url"}]}
    empty_title = {**PROFILE, "evidence": [{"kind": "text", "title": "", "content": "sample"}]}
    for body in (bad_service, bad_link, empty_title):
        assert client.put("/profile", json=body, headers=owner_a).status_code == 422
    assert client.get("/profile", headers=owner_a).json()["version"] == 1
