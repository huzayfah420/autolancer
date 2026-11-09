"""AI assessment within the daily cap, then rule classification (rows 7-8, UC-002 steps 3-6).

An assessment is "current" when its listing, profile and policy versions all match the
live ones. Changing any of them makes it stale, which queues the job for re-assessment.
"""

import json
import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..llm import LLMError, complete_json
from ..models import Assessment, Listing, PolicyVersion, Profile
from ..rules import classify
from ..schemas import SERVICES, AIAssessment
from .common import active_policy, cap_reached, daily_cap, get_profile, record_usage, spent_today
from .discovery import PreconditionError

SYSTEM_PROMPT = (
    "You assess freelance job listings for one freelancer (the owner). Using only the listing and "
    "the owner's services, skills summary and evidence, return: category (one of finance, software, "
    "data, research, writing, other); fit from 0 to 1 for how well the owner's evidenced skills match; "
    "1-6 short fit_reasons; expected deliverables; effort_hours_min/max; a sensible price_min/max in the "
    "listing currency; uncertainty (low/medium/high) about scope and estimates; and open_questions only "
    "for information the owner genuinely needs from the client. Finance expertise is an extra fit "
    "signal for finance jobs but must not lower fit for suitable general work. Be honest: do not "
    "overstate fit beyond the evidence."
)


# ---- Inputs ----

def build_input(listing: Listing, profile: Profile) -> str:
    """Permitted inputs only. Client identity (name, country, rating) is never sent (AIR-001)."""
    return json.dumps(
        {
            "listing": {
                "title": listing.title,
                "description": listing.description,
                "category_hint": listing.category,
                "budget": [listing.budget_min, listing.budget_max],
                "currency": listing.currency,
                "deadline_days": listing.deadline_days,
                "skills": listing.skills,
            },
            "owner": {
                "services": profile.services,
                "skills_summary": profile.skills_summary,
                "evidence": [{"title": e["title"], "content": e["content"][:500]} for e in profile.evidence],
            },
        },
        indent=1,
    )


def mock_assessment(listing: Listing, profile: Profile) -> dict:
    """Deterministic stand-in for the model, driven by skill overlap with the profile text."""
    category = listing.category if listing.category in SERVICES else "other"
    profile_text = (profile.skills_summary + " " + " ".join(e["title"] + " " + e["content"] for e in profile.evidence)).lower()
    overlap = [s for s in listing.skills if s.lower() in profile_text]
    fit = min(0.95, 0.55 + 0.15 * len(overlap)) if category in profile.services else 0.15
    effort_mid = max(4.0, round((listing.budget_min + listing.budget_max) / 2 / 60))  # about $60/hour
    unclear = bool(re.search(r"\bTBD\b|to be confirmed", listing.description, re.I))
    return {
        "category": category,
        "fit": round(fit, 2),
        "fit_reasons": [f"Matching skills: {', '.join(overlap)}" if overlap else "No listed skill appears in your profile"],
        "deliverables": [f"{listing.title} - final deliverable"],
        "effort_hours_min": round(effort_mid * 0.8, 1),
        "effort_hours_max": round(effort_mid * 1.3, 1),
        "price_min": listing.budget_min,
        "price_max": listing.budget_max,
        "uncertainty": "high" if len(listing.description) < 160 else ("medium" if unclear else "low"),
        "open_questions": ["Please confirm the details marked TBD."] if unclear else [],
    }


# ---- Current / stale ----

def latest_by_listing(db: Session, owner_id: uuid.UUID) -> dict[int, Assessment]:
    """Newest assessment row for each listing of this owner."""
    rows = db.scalars(select(Assessment).where(Assessment.owner_id == owner_id).order_by(Assessment.id))
    return {a.listing_id: a for a in rows}


def is_current(a: Assessment | None, listing: Listing, profile: Profile, policy: PolicyVersion | None) -> bool:
    return (
        a is not None
        and policy is not None
        and a.status == "assessed"
        and a.listing_version == listing.version
        and a.profile_version == profile.version
        and a.policy_version == policy.version
    )


# ---- Assess ----

def assess_listing(db: Session, owner_id: uuid.UUID, listing: Listing, profile: Profile, policy: PolicyVersion) -> Assessment:
    """Assess one listing and store the result (assessed or unassessed with a reason)."""
    row = Assessment(
        owner_id=owner_id, listing_id=listing.id, listing_version=listing.version,
        profile_version=profile.version, policy_version=policy.version, status="unassessed",
    )

    def unassessed(reason: str) -> Assessment:
        row.unassessed_reason = reason
        db.add(row)
        db.commit()
        return row

    if "assess_jobs" not in policy.allowed_actions:
        return unassessed("Your policy does not allow AI assessment.")
    if not profile.services:
        return unassessed("Add at least one service to your profile.")

    # UC-002 A1: if only the policy changed, reuse the AI output and rerun the rules (no new cost).
    reusable = db.scalar(
        select(Assessment)
        .where(
            Assessment.owner_id == owner_id, Assessment.listing_id == listing.id,
            Assessment.listing_version == listing.version, Assessment.profile_version == profile.version,
            Assessment.status == "assessed",
        )
        .order_by(Assessment.id.desc())
        .limit(1)
    )
    if reusable is not None:
        ai = AIAssessment.model_validate(reusable.ai_output)
        row.reused_ai_output = True
    else:
        if cap_reached(db, owner_id):
            return unassessed(
                f"Daily AI spending cap reached (${spent_today(db, owner_id):.4f} of ${daily_cap(db, owner_id):.2f})."
            )
        try:
            ai, usage = complete_json(
                SYSTEM_PROMPT, build_input(listing, profile), AIAssessment, lambda: mock_assessment(listing, profile)
            )
        except LLMError as e:
            record_usage(db, owner_id, "assessment", e.usage, ok=False, error=str(e), listing_id=listing.id)
            return unassessed(f"AI assessment failed: {e}")
        record_usage(db, owner_id, "assessment", usage, ok=True, listing_id=listing.id)

    result = classify(listing, ai, profile, policy)
    row.status = "assessed"
    row.ai_output = ai.model_dump()
    row.classification = result.classification
    row.score = result.score
    row.score_breakdown = result.breakdown
    row.pursue_eligible = result.pursue_eligible
    row.rule_reasons = result.reasons
    db.add(row)
    db.commit()
    return row


def assess_pending(db: Session, owner_id: uuid.UUID, listing_id: int | None = None) -> dict:
    """Assess every listing (or one) that has no current assessment."""
    policy = active_policy(db, owner_id)
    if policy is None:
        raise PreconditionError("Save a policy first.")
    profile = get_profile(db, owner_id)
    latest = latest_by_listing(db, owner_id)

    query = select(Listing).where(Listing.owner_id == owner_id).order_by(Listing.id)
    if listing_id is not None:
        query = query.where(Listing.id == listing_id)
    counts = {"assessed": 0, "reused": 0, "unassessed": 0, "already_current": 0}
    for listing in db.scalars(query).all():
        if is_current(latest.get(listing.id), listing, profile, policy):
            counts["already_current"] += 1
            continue
        row = assess_listing(db, owner_id, listing, profile, policy)
        if row.status == "unassessed":
            counts["unassessed"] += 1
        else:
            counts["reused" if row.reused_ai_output else "assessed"] += 1
    return counts
