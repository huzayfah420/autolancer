"""The ranked job feed (row 9, UC-002 step 7, FR-006, FR-025)."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Assessment, Listing
from .assessment import is_current, latest_by_listing
from .common import active_policy, daily_cap, get_connection, get_profile, spent_today


def same_instant(a: datetime | None, b: datetime | None) -> bool:
    """Compare timestamps that may come back naive (SQLite) or aware (Postgres)."""
    if a is None or b is None:
        return False
    if (a.tzinfo is None) != (b.tzinfo is None):
        a, b = a.replace(tzinfo=None), b.replace(tzinfo=None)
    return a == b


def job_status(latest: Assessment | None, current: bool) -> str:
    """pending = never assessed, stale = inputs changed since, unassessed = failed/skipped."""
    if latest is None:
        return "pending"
    if latest.status == "unassessed":
        return "unassessed"
    return "assessed" if current else "stale"


def summarize(listing: Listing, latest: Assessment | None, current: bool, last_fetch_at) -> dict:
    status = job_status(latest, current)
    has_result = latest is not None and latest.status == "assessed"
    ai = latest.ai_output if has_result else None
    is_new = same_instant(listing.first_seen_at, last_fetch_at)
    return {
        "id": listing.id,
        "source_id": listing.source_id,
        "title": listing.title,
        "category": listing.category,
        "budget_min": listing.budget_min,
        "budget_max": listing.budget_max,
        "currency": listing.currency,
        "deadline_days": listing.deadline_days,
        "skills": listing.skills,
        "url": listing.url,
        "simulated": listing.simulated,
        "version": listing.version,
        "is_new": is_new,
        "is_changed": not is_new and same_instant(listing.changed_at, last_fetch_at),
        "status": status,
        "unassessed_reason": latest.unassessed_reason if status == "unassessed" else None,
        # Results of a stale assessment are still shown, but labelled and never eligible.
        "classification": latest.classification if has_result else None,
        "score": latest.score if has_result else None,
        "fit": ai["fit"] if ai else None,
        "uncertainty": ai["uncertainty"] if ai else None,
        "pursue_eligible": bool(current and latest.pursue_eligible),
        "rule_reasons": latest.rule_reasons if has_result else [],
    }


def build_feed(db: Session, owner_id: uuid.UUID, filters: dict) -> dict:
    conn = get_connection(db, owner_id)
    profile = get_profile(db, owner_id)
    policy = active_policy(db, owner_id)
    latest = latest_by_listing(db, owner_id)

    items = []
    for listing in db.scalars(select(Listing).where(Listing.owner_id == owner_id)).all():
        a = latest.get(listing.id)
        items.append(summarize(listing, a, is_current(a, listing, profile, policy), conn.last_fetch_at))

    needs_assessment = sum(1 for i in items if i["status"] != "assessed")
    q = (filters.get("q") or "").strip().lower()
    items = [
        i for i in items
        if (not filters.get("classification") or i["classification"] == filters["classification"])
        and (not filters.get("category") or i["category"] == filters["category"])
        and (not filters.get("status") or i["status"] == filters["status"])
        and (not filters.get("eligible_only") or i["pursue_eligible"])
        and (not filters.get("changes_only") or i["is_new"] or i["is_changed"])
        and (not q or q in i["title"].lower() or any(q in s.lower() for s in i["skills"]))
    ]
    # Highest score first; jobs without a score go last.
    items.sort(key=lambda i: (i["score"] is None, -(i["score"] or 0), i["id"]))

    return {
        "items": items,
        "needs_assessment": needs_assessment,
        "last_fetch_at": conn.last_fetch_at,
        "last_fetch_attempt_at": conn.last_fetch_attempt_at,
        "last_fetch_error": conn.last_fetch_error,
        "last_fetch_attempts": conn.last_fetch_attempts,
        "connected": conn.enabled and conn.status == "connected",
        "policy_version": policy.version if policy else None,
        "profile_version": profile.version,
        "ai_spent_today": round(spent_today(db, owner_id), 6),
        "ai_daily_cap": daily_cap(db, owner_id),
    }


def job_detail(db: Session, owner_id: uuid.UUID, listing_id: int) -> dict | None:
    """Everything the side drawer shows, or None if the job is not this owner's."""
    listing = db.scalar(select(Listing).where(Listing.owner_id == owner_id, Listing.id == listing_id))
    if listing is None:
        return None
    conn = get_connection(db, owner_id)
    profile = get_profile(db, owner_id)
    policy = active_policy(db, owner_id)
    history = db.scalars(
        select(Assessment)
        .where(Assessment.owner_id == owner_id, Assessment.listing_id == listing_id)
        .order_by(Assessment.id.desc())
    ).all()
    latest = history[0] if history else None
    current = is_current(latest, listing, profile, policy)
    return {
        **summarize(listing, latest, current, conn.last_fetch_at),
        "description": listing.description,
        "client": listing.client,
        "posted_at": listing.posted_at,
        "ai_output": latest.ai_output if latest and latest.status == "assessed" else None,
        "score_breakdown": latest.score_breakdown if latest and latest.status == "assessed" else None,
        "reused_ai_output": bool(latest and latest.reused_ai_output),
        "assessed_with": (
            {"listing": latest.listing_version, "profile": latest.profile_version, "policy": latest.policy_version}
            if latest else None
        ),
        "current_versions": {"listing": listing.version, "profile": profile.version, "policy": policy.version if policy else None},
        "history": [
            {
                "id": a.id, "created_at": a.created_at, "status": a.status, "classification": a.classification,
                "score": a.score, "unassessed_reason": a.unassessed_reason,
                "versions": {"listing": a.listing_version, "profile": a.profile_version, "policy": a.policy_version},
            }
            for a in history[:20]
        ],
    }
