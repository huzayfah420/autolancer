"""Row 9: ranked feed with filters, new/changed markers, AI reasons and pursue-eligible flag
(UC-002 step 7, FR-006, FR-025)."""

from tests.conftest import POLICY


def feed(client, headers, **params):
    return client.get("/jobs", headers=headers, params=params).json()


def test_ranked_by_decision_then_score(client, ready_a):
    items = feed(client, ready_a)["items"]
    # Pursue jobs first, then clarify, then decline; highest score first inside each group.
    tiers = [["pursue", "clarify", "decline"].index(j["classification"]) for j in items]
    assert tiers == sorted(tiers)
    for name in ("pursue", "clarify", "decline"):
        scores = [j["score"] for j in items if j["classification"] == name]
        assert scores and scores == sorted(scores, reverse=True)


def test_filters(client, ready_a):
    for c in ("pursue", "clarify", "decline"):
        items = feed(client, ready_a, classification=c)["items"]
        assert items and all(j["classification"] == c for j in items)
    assert all(j["category"] == "data" for j in feed(client, ready_a, category="data")["items"])
    eligible = feed(client, ready_a, eligible_only=True)["items"]
    assert eligible and all(j["pursue_eligible"] and j["classification"] == "pursue" for j in eligible)
    assert [j["source_id"] for j in feed(client, ready_a, q="churn")["items"]] == ["SIM-1013"]
    assert client.get("/jobs", headers=ready_a, params={"classification": "maybe"}).status_code == 422


def test_new_and_changed_markers(client, ready_a):
    assert all(j["is_new"] for j in feed(client, ready_a)["items"])  # first fetch: everything is new

    client.post("/sim/chaos/edit-listing/SIM-1002")
    client.post("/sim/chaos/add-listing")
    client.post("/jobs/fetch", headers=ready_a)
    items = {j["source_id"]: j for j in feed(client, ready_a)["items"]}
    assert items["SIM-2001"]["is_new"] and not items["SIM-2001"]["is_changed"]
    assert items["SIM-1002"]["is_changed"] and not items["SIM-1002"]["is_new"]
    assert not items["SIM-1003"]["is_new"] and not items["SIM-1003"]["is_changed"]
    assert {j["source_id"] for j in feed(client, ready_a, changes_only=True)["items"]} == {"SIM-2001", "SIM-1002"}


def test_detail_shows_ai_reasons_and_versions(client, ready_a):
    job_id = feed(client, ready_a, q="13-week")["items"][0]["id"]
    d = client.get(f"/jobs/{job_id}", headers=ready_a).json()
    assert d["ai_output"]["fit_reasons"] and d["ai_output"]["deliverables"]
    assert d["ai_output"]["assumptions"] and d["ai_output"]["expected_return_basis"]
    assert set(d["score_breakdown"]["parts"]) == {"fit", "effort", "deadline", "price", "certainty"}
    assert d["score_breakdown"]["expected_return"]["hourly_rate"] > 0
    assert d["rule_reasons"]
    assert d["assessed_with"] == d["current_versions"] == {"listing": 1, "profile": 2, "policy": 1}
    assert d["client"]["name"] and len(d["history"]) == 1


def test_stale_jobs_are_labelled_and_not_eligible(client, ready_a):
    assert any(j["pursue_eligible"] for j in feed(client, ready_a)["items"])
    client.post("/policy", json={**POLICY, "max_bid": 2500}, headers=ready_a)
    body = feed(client, ready_a)
    assert body["needs_assessment"] == 27 and body["policy_version"] == 2
    assert all(j["status"] == "stale" and not j["pursue_eligible"] for j in body["items"])
    assert all(j["status"] == "stale" for j in feed(client, ready_a, status="stale")["items"])


def test_feed_reports_spend_and_last_update(client, ready_a):
    body = feed(client, ready_a)
    assert body["connected"] and body["last_fetch_at"] and body["last_fetch_error"] is None
    assert 0 < body["ai_spent_today"] <= body["ai_daily_cap"]
