"""Row 7: AI assessment within the daily cap; failures become unassessed and can be retried
(UC-002 steps 3-4, E2, FR-006, AIR-001)."""

from sqlalchemy import select

from app.llm import LLMError, Usage
from app.models import AIUsage
from app.services import assessment as assessment_service
from tests.conftest import POLICY, setup_owner


def usage_rows(session_factory):
    with session_factory() as db:
        return db.scalars(select(AIUsage).where(AIUsage.purpose == "assessment")).all()


def test_every_new_job_is_assessed_and_costed(client, ready_a, session_factory):
    feed = client.get("/jobs", headers=ready_a).json()
    assert all(j["status"] == "assessed" for j in feed["items"])
    rows = usage_rows(session_factory)
    assert len(rows) == 27 and all(r.ok and r.cost_usd > 0 for r in rows)
    assert feed["ai_spent_today"] == round(sum(r.cost_usd for r in rows), 6)


def test_over_cap_jobs_become_unassessed(client, owner_a, session_factory):
    # Mock calls cost $0.001 each and reserve that much before they start, so a third call
    # (which would take spend to $0.003) is refused: the cap is never overshot (NFR-011).
    setup_owner(client, owner_a, policy={**POLICY, "daily_ai_cap_usd": 0.0025})
    result = client.post("/jobs/fetch", headers=owner_a).json()["assessment"]
    assert result["assessed"] == 2 and result["unassessed"] == 25
    rows = usage_rows(session_factory)
    assert len(rows) == 2  # no model call once the next one would pass the cap
    assert sum(r.cost_usd for r in rows) <= 0.0025

    items = client.get("/jobs", headers=owner_a).json()["items"]
    unassessed = [j for j in items if j["status"] == "unassessed"]
    assert len(unassessed) == 25
    assert all("cap reached" in j["unassessed_reason"] for j in unassessed)
    assert not any(j["pursue_eligible"] for j in unassessed)

    # Retry stays unassessed while capped, then works once the cap is raised.
    job_id = unassessed[0]["id"]
    assert client.post(f"/jobs/{job_id}/assess", headers=owner_a).json()["status"] == "unassessed"
    client.post("/policy", json={**POLICY, "daily_ai_cap_usd": 1.0}, headers=owner_a)
    assert client.post(f"/jobs/{job_id}/assess", headers=owner_a).json()["status"] == "assessed"


def test_failed_call_is_unassessed_and_retry_works(client, owner_a, session_factory, monkeypatch):
    setup_owner(client, owner_a)

    def fail(*args, **kwargs):
        raise LLMError("Model call failed: Timeout", Usage("mock"))

    monkeypatch.setattr(assessment_service, "complete_json", fail)
    client.post("/jobs/fetch", headers=owner_a)
    items = client.get("/jobs", headers=owner_a).json()["items"]
    assert all(j["status"] == "unassessed" and "Timeout" in j["unassessed_reason"] for j in items)
    assert all(not r.ok for r in usage_rows(session_factory))  # failed calls are still recorded

    monkeypatch.undo()
    job = client.post(f"/jobs/{items[0]['id']}/assess", headers=owner_a).json()
    assert job["status"] == "assessed" and job["classification"] in {"pursue", "clarify", "decline"}


def test_invalid_json_is_unassessed(client, owner_a, monkeypatch):
    setup_owner(client, owner_a)
    # The "model" returns output that breaks the schema (fit must be 0..1, ranges ordered).
    monkeypatch.setattr(
        assessment_service, "mock_assessment",
        lambda listing, profile: {"category": "finance", "fit": 7, "fit_reasons": [], "effort_hours_min": 5,
                                  "effort_hours_max": 1, "price_min": 1, "price_max": 2, "uncertainty": "low"},
    )
    client.post("/jobs/fetch", headers=owner_a)
    items = client.get("/jobs", headers=owner_a).json()["items"]
    assert all(j["status"] == "unassessed" and "Invalid model output" in j["unassessed_reason"] for j in items)


def test_policy_can_forbid_assessment(client, owner_a, session_factory):
    setup_owner(client, owner_a, policy={**POLICY, "allowed_actions": ["discover_jobs"]})
    client.post("/jobs/fetch", headers=owner_a)
    items = client.get("/jobs", headers=owner_a).json()["items"]
    assert all("does not allow AI assessment" in j["unassessed_reason"] for j in items)
    assert usage_rows(session_factory) == []


def test_client_identity_is_not_sent_to_the_model(client, ready_a, session_factory):
    from app.models import Listing, Profile

    with session_factory() as db:
        listing = db.scalars(select(Listing)).first()
        profile = db.scalars(select(Profile)).first()
    prompt = assessment_service.build_input(listing, profile)
    assert listing.client["name"] not in prompt and '"client"' not in prompt and '"rating"' not in prompt
