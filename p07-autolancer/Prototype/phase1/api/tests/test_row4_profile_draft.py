"""Row 4: AI profile draft with unsupported claims; accept or ignore (UC-001 step 5, A2, E3, AIR-002)."""

from sqlalchemy import select

from app.llm import LLMError, Usage
from app.models import AIUsage
from app.routers import profile as profile_router
from tests.conftest import POLICY, PROFILE

# Evidence mentions finance and software but not data, so "data" is unsupported.


def test_draft_returns_text_and_unsupported_claims(client, owner_a, session_factory):
    client.put("/profile", json=PROFILE, headers=owner_a)
    p = client.post("/profile/draft", headers=owner_a).json()
    assert p["pending_draft"]
    assert "data" not in p["pending_draft"]  # unsupported service left out (FR-003 AC-1)
    assert p["pending_unsupported_claims"] == ["No evidence provided for data work"]
    assert p["version"] == 2  # a draft alone changes nothing

    with session_factory() as db:
        usage = db.scalars(select(AIUsage)).all()
    assert len(usage) == 1 and usage[0].purpose == "profile_draft" and usage[0].cost_usd > 0


def test_accept_replaces_summary_and_bumps_version(client, owner_a):
    client.put("/profile", json=PROFILE, headers=owner_a)
    draft = client.post("/profile/draft", headers=owner_a).json()["pending_draft"]
    p = client.post("/profile/draft/accept", headers=owner_a).json()
    assert p["skills_summary"] == draft and p["version"] == 3 and p["pending_draft"] is None


def test_ignore_keeps_own_profile(client, owner_a):
    client.put("/profile", json=PROFILE, headers=owner_a)
    client.post("/profile/draft", headers=owner_a)
    p = client.delete("/profile/draft", headers=owner_a).json()
    assert p["skills_summary"] == PROFILE["skills_summary"] and p["version"] == 2 and p["pending_draft"] is None
    assert client.post("/profile/draft/accept", headers=owner_a).status_code == 404


def test_generation_failure_shows_reason_and_records_cost(client, owner_a, session_factory, monkeypatch):
    client.put("/profile", json=PROFILE, headers=owner_a)

    def fail(*args, **kwargs):
        raise LLMError("Invalid model output: 1 validation errors", Usage("mock", 10, 5, 0.002))

    monkeypatch.setattr(profile_router, "complete_json", fail)
    r = client.post("/profile/draft", headers=owner_a)
    assert r.status_code == 502 and "could not be generated" in r.json()["detail"]
    assert client.get("/profile", headers=owner_a).json()["skills_summary"] == PROFILE["skills_summary"]
    with session_factory() as db:
        row = db.scalars(select(AIUsage)).one()
    assert row.ok is False and row.cost_usd == 0.002


def test_draft_needs_services(client, owner_a):
    assert client.post("/profile/draft", headers=owner_a).status_code == 400


def test_draft_respects_daily_cap(client, owner_a):
    client.put("/profile", json=PROFILE, headers=owner_a)
    client.post("/policy", json={**POLICY, "daily_ai_cap_usd": 0}, headers=owner_a)
    r = client.post("/profile/draft", headers=owner_a)
    assert r.status_code == 409 and "cap" in r.json()["detail"]
