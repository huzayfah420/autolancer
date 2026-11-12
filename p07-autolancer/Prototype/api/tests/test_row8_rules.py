"""Row 8: pursue/clarify/decline rules, weighted score, versioned re-assessment
(UC-002 steps 5-6, A1, A2, E3, FR-006)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.models import AIUsage, Assessment, Listing, PolicyVersion, Profile
from app.rules import WEIGHTS, classify
from app.schemas import AIAssessment
from tests.conftest import POLICY, PROFILE

NOW = datetime.now(timezone.utc)


def make_listing(**kw) -> Listing:
    base = dict(
        owner_id=uuid.uuid4(), source="simulator", source_id="X", title="Cash-flow model", description="A clear brief " * 20,
        category="finance", budget_min=1000, budget_max=2000, currency="USD", deadline_days=14, skills=["excel"],
        client={}, content_hash="h", version=1, first_seen_at=NOW, changed_at=NOW, last_seen_at=NOW,
    )
    return Listing(**{**base, **kw})


def make_ai(**kw) -> AIAssessment:
    base = dict(category="finance", fit=0.8, fit_reasons=["Matches evidence"], effort_hours_min=10, effort_hours_max=20,
                price_min=1200, price_max=1800, uncertainty="low", open_questions=[],
                assumptions=["Data supplied at kickoff"], expected_return_basis="About $100/hour.")
    return AIAssessment(**{**base, **kw})


PROFILE_ROW = Profile(services=["finance", "software"], skills_summary="", evidence=[], version=1)


def policy_row(**kw) -> PolicyVersion:
    # Built in memory, so the column default does not apply: set every field explicitly.
    return PolicyVersion(version=1, **{"min_deadline_days": 0, **POLICY, **kw})


# ---- Unit tests of the rules ----

def test_pursue_and_eligible():
    r = classify(make_listing(), make_ai(), PROFILE_ROW, policy_row())
    assert r.classification == "pursue" and r.pursue_eligible


def test_decline_reasons():
    cases = [
        (make_listing(), make_ai(category="writing"), "not one of your services"),
        (make_listing(), make_ai(fit=0.2), "below 0.4"),
        (make_listing(budget_max=100), make_ai(), "below your minimum"),
        (make_listing(description="Pays in crypto only"), make_ai(), "excluded keyword 'crypto'"),
        (make_listing(deadline_days=1), make_ai(effort_hours_min=40, effort_hours_max=60), "available before the deadline"),
    ]
    for listing, ai, reason in cases:
        r = classify(listing, ai, PROFILE_ROW, policy_row())
        assert r.classification == "decline" and not r.pursue_eligible
        assert any(reason in x for x in r.reasons), (reason, r.reasons)


def test_deadline_limit_declines_short_jobs():
    policy = policy_row(min_deadline_days=10)
    r = classify(make_listing(deadline_days=7), make_ai(), PROFILE_ROW, policy)
    assert r.classification == "decline" and any("10-day deadline limit" in x for x in r.reasons)
    assert classify(make_listing(deadline_days=10), make_ai(), PROFILE_ROW, policy).classification == "pursue"


def test_clarify_reasons():
    for ai, reason in [
        (make_ai(open_questions=["Which ERP?"]), "open question"),
        (make_ai(uncertainty="high"), "uncertainty is high"),
        (make_ai(fit=0.5), "borderline"),
    ]:
        r = classify(make_listing(), ai, PROFILE_ROW, policy_row())
        assert r.classification == "clarify" and not r.pursue_eligible
        assert any(reason in x for x in r.reasons)


def test_policy_blocks_eligibility_but_keeps_pursue():
    blocked = [
        (policy_row(allowed_actions=["discover_jobs", "assess_jobs"]), "submitting proposals"),
        (policy_row(daily_proposal_limit=0), "proposal limit"),
        (policy_row(workload_limit=0), "Workload limit"),
        (policy_row(max_bid=1000), "exceeds max bid"),
        (policy_row(review_conditions=["finance_jobs"]), "finance job"),
    ]
    for policy, reason in blocked:
        r = classify(make_listing(), make_ai(), PROFILE_ROW, policy)
        assert r.classification == "pursue" and not r.pursue_eligible
        assert any(reason in x for x in r.reasons)
    r = classify(make_listing(deadline_days=2), make_ai(effort_hours_min=2, effort_hours_max=4), PROFILE_ROW,
                 policy_row(review_conditions=["short_deadline"]))
    assert not r.pursue_eligible


def test_score_is_weighted_sum():
    r = classify(make_listing(), make_ai(), PROFILE_ROW, policy_row())
    parts = r.breakdown["parts"]
    assert set(parts) == {"fit", "effort", "deadline", "price", "certainty"} and abs(sum(WEIGHTS.values()) - 1) < 1e-9
    assert r.score == round(100 * sum(WEIGHTS[k] * parts[k] for k in parts), 1)
    better = classify(make_listing(), make_ai(fit=0.95), PROFILE_ROW, policy_row())
    assert better.score > r.score


def test_uncertainty_lowers_rank():
    scores = [classify(make_listing(), make_ai(uncertainty=u), PROFILE_ROW, policy_row()).score for u in ("low", "medium", "high")]
    assert scores[0] > scores[1] > scores[2]


def test_expected_return_basis():
    # Price mid 1500, effort mid 15h -> $100/hour.
    er = classify(make_listing(), make_ai(), PROFILE_ROW, policy_row()).breakdown["expected_return"]
    assert er == {"price": 1500, "effort_hours": 15, "hourly_rate": 100}


# ---- Versioned re-assessment through the API ----

def latest(session_factory, source_id: str) -> Assessment:
    with session_factory() as db:
        lid = db.scalar(select(Listing.id).where(Listing.source_id == source_id))
        return db.scalars(select(Assessment).where(Assessment.listing_id == lid).order_by(Assessment.id.desc())).first()


def model_calls(session_factory) -> int:
    with session_factory() as db:
        return len(db.scalars(select(AIUsage).where(AIUsage.purpose == "assessment")).all())


def test_assessment_stores_versions_used(client, ready_a, session_factory):
    a = latest(session_factory, "SIM-1001")
    assert (a.listing_version, a.profile_version, a.policy_version) == (1, 2, 1)


def test_nothing_reassessed_without_changes(client, ready_a, session_factory):
    result = client.post("/jobs/assess", headers=ready_a).json()
    assert result == {"assessed": 0, "reused": 0, "unassessed": 0, "already_current": 27}


def test_listing_change_reassesses_only_that_job(client, ready_a, session_factory):
    calls = model_calls(session_factory)
    client.post("/sim/chaos/edit-listing/SIM-1001")
    result = client.post("/jobs/fetch", headers=ready_a).json()["assessment"]
    assert result["assessed"] == 1 and result["already_current"] == 26
    assert model_calls(session_factory) == calls + 1
    assert latest(session_factory, "SIM-1001").listing_version == 2


def test_profile_change_reassesses_all_jobs(client, ready_a, session_factory):
    calls = model_calls(session_factory)
    client.put("/profile", json={**PROFILE, "skills_summary": "Excel and Python only."}, headers=ready_a)
    feed = client.get("/jobs", headers=ready_a).json()
    assert feed["needs_assessment"] == 27 and all(j["status"] == "stale" and not j["pursue_eligible"] for j in feed["items"])

    result = client.post("/jobs/assess", headers=ready_a).json()
    assert result["assessed"] == 27
    assert model_calls(session_factory) == calls + 27
    assert latest(session_factory, "SIM-1001").profile_version == 3


def test_policy_change_reassesses_with_rules_only(client, ready_a, session_factory):
    calls = model_calls(session_factory)
    before = latest(session_factory, "SIM-1002")
    assert before.classification == "pursue" and before.pursue_eligible

    client.post("/policy", json={**POLICY, "review_conditions": ["finance_jobs"]}, headers=ready_a)
    result = client.post("/jobs/assess", headers=ready_a).json()
    assert result["reused"] == 27 and result["assessed"] == 0
    assert model_calls(session_factory) == calls  # UC-002 A1: no new AI cost for a policy-only change

    after = latest(session_factory, "SIM-1002")
    assert after.policy_version == 2 and after.reused_ai_output
    assert after.classification == "pursue" and not after.pursue_eligible
    assert "Review required: finance job" in after.rule_reasons


def test_policy_change_can_decline_stored_jobs(client, ready_a, session_factory):
    client.post("/policy", json={**POLICY, "excluded_keywords": ["dashboard"]}, headers=ready_a)
    client.post("/jobs/assess", headers=ready_a)
    a = latest(session_factory, "SIM-1001")
    assert a.classification == "decline" and any("dashboard" in r for r in a.rule_reasons)


def test_deadline_limit_change_reranks_without_ai_cost(client, ready_a, session_factory):
    calls = model_calls(session_factory)
    client.post("/policy", json={**POLICY, "min_deadline_days": 10}, headers=ready_a)
    result = client.post("/jobs/assess", headers=ready_a).json()
    assert result["reused"] == 27 and model_calls(session_factory) == calls
    a = latest(session_factory, "SIM-1003")  # due in 7 days
    assert a.classification == "decline" and any("deadline limit" in r for r in a.rule_reasons)


def test_old_format_ai_output_is_reassessed_not_reused(client, ready_a, session_factory):
    # An assessment stored before assumptions/expected_return_basis existed cannot be reused.
    with session_factory() as db:
        for a in db.scalars(select(Assessment)).all():
            a.ai_output = {k: v for k, v in a.ai_output.items() if k != "expected_return_basis"}
        db.commit()
    calls = model_calls(session_factory)
    client.post("/policy", json={**POLICY, "max_bid": 2500}, headers=ready_a)
    result = client.post("/jobs/assess", headers=ready_a).json()
    assert result["assessed"] == 27 and result["reused"] == 0
    assert model_calls(session_factory) == calls + 27
