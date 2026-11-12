"""Jobs: fetch, assess, retry, feed and detail (rows 6-9, UC-002)."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import Owner, current_owner
from ..db import get_db
from ..marketplace import SimulatorAdapter, get_marketplace
from ..services.assessment import assess_pending
from ..services.discovery import PreconditionError, fetch_jobs
from ..services.feed import build_feed, job_detail

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
def feed(
    classification: Literal["pursue", "clarify", "decline"] | None = None,
    category: str | None = None,
    status: Literal["assessed", "stale", "unassessed", "pending"] | None = None,
    eligible_only: bool = False,
    changes_only: bool = False,
    q: str | None = None,
    owner: Owner = Depends(current_owner),
    db: Session = Depends(get_db),
):
    filters = {
        "classification": classification, "category": category, "status": status,
        "eligible_only": eligible_only, "changes_only": changes_only, "q": q,
    }
    return build_feed(db, owner.id, filters)


@router.post("/fetch")
def fetch(
    owner: Owner = Depends(current_owner),
    db: Session = Depends(get_db),
    market: SimulatorAdapter = Depends(get_marketplace),
):
    """One discovery cycle: fetch + store, then assess whatever is not current."""
    try:
        result = fetch_jobs(db, owner.id, market)
        assessment = assess_pending(db, owner.id) if result["ok"] else None
    except PreconditionError as e:
        raise HTTPException(409, str(e))
    return {"fetch": result, "assessment": assessment}


@router.post("/assess")
def assess_all(owner: Owner = Depends(current_owner), db: Session = Depends(get_db)):
    """Re-assess jobs made stale by a profile, policy or listing change (no fetch)."""
    try:
        return assess_pending(db, owner.id)
    except PreconditionError as e:
        raise HTTPException(409, str(e))


@router.post("/{listing_id}/assess")
def retry_one(listing_id: int, owner: Owner = Depends(current_owner), db: Session = Depends(get_db)):
    """The Retry button for one unassessed job."""
    if job_detail(db, owner.id, listing_id) is None:
        raise HTTPException(404, "Job not found")
    try:
        assess_pending(db, owner.id, listing_id=listing_id)
    except PreconditionError as e:
        raise HTTPException(409, str(e))
    return job_detail(db, owner.id, listing_id)


@router.get("/{listing_id}")
def detail(listing_id: int, owner: Owner = Depends(current_owner), db: Session = Depends(get_db)):
    job = job_detail(db, owner.id, listing_id)
    if job is None:
        # Same 404 whether the job does not exist or belongs to someone else (FR-001 AC-2).
        raise HTTPException(404, "Job not found")
    return job
