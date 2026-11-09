"""Profile form and "Draft my profile" (rows 3-4, UC-001 steps 4-5, A2, E3, FR-003, AIR-002)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import Owner, current_owner
from ..db import get_db
from ..llm import LLMError, complete_json
from ..models import Profile, utcnow
from ..schemas import ProfileIn
from ..services.common import cap_reached, get_profile, record_usage
from ..services.profile_ai import draft_args, ground_claims

router = APIRouter(prefix="/profile", tags=["profile"])


def profile_out(p: Profile) -> dict:
    return {
        "version": p.version,
        "services": p.services,
        "skills_summary": p.skills_summary,
        "evidence": p.evidence,
        "pending_draft": p.pending_draft,
        "pending_unsupported_claims": p.pending_unsupported_claims,
        "pending_claims": p.pending_claims,
        "updated_at": p.updated_at,
    }


def bump(p: Profile) -> None:
    """A new profile version makes every assessment stale (row 8)."""
    p.version += 1
    p.updated_at = utcnow()


@router.get("")
def read_profile(owner: Owner = Depends(current_owner), db: Session = Depends(get_db)):
    return profile_out(get_profile(db, owner.id))


@router.put("")
def save_profile(body: ProfileIn, owner: Owner = Depends(current_owner), db: Session = Depends(get_db)):
    p = get_profile(db, owner.id)
    new = body.model_dump()
    # Only a real change creates a new version, so re-saving does not trigger re-assessment.
    if (p.services, p.skills_summary, p.evidence) != (new["services"], new["skills_summary"], new["evidence"]):
        p.services, p.skills_summary, p.evidence = new["services"], new["skills_summary"], new["evidence"]
        bump(p)
        db.commit()
    return profile_out(p)


@router.post("/draft")
def draft_profile(owner: Owner = Depends(current_owner), db: Session = Depends(get_db)):
    p = get_profile(db, owner.id)
    if not p.services:
        raise HTTPException(400, "Save at least one service before asking for a draft.")
    if cap_reached(db, owner.id):
        raise HTTPException(409, "Daily AI spending cap reached. Try again tomorrow or raise the cap in your policy.")
    try:
        result, usage = complete_json(*draft_args(p))
    except LLMError as e:
        # E3: record the cost, keep the owner's profile and any earlier draft, show the reason.
        record_usage(db, owner.id, "profile_draft", e.usage, ok=False, error=str(e))
        db.commit()
        raise HTTPException(502, f"The profile draft could not be generated: {e}")
    record_usage(db, owner.id, "profile_draft", usage, ok=True)
    claims, unsupported = ground_claims(result, p)
    p.pending_draft, p.pending_claims, p.pending_unsupported_claims = result.draft, claims, unsupported
    db.commit()
    return profile_out(p)


@router.post("/draft/accept")
def accept_draft(owner: Owner = Depends(current_owner), db: Session = Depends(get_db)):
    p = get_profile(db, owner.id)
    if not p.pending_draft:
        raise HTTPException(404, "There is no draft to accept.")
    p.skills_summary = p.pending_draft
    p.pending_draft, p.pending_claims, p.pending_unsupported_claims = None, None, None
    bump(p)
    db.commit()
    return profile_out(p)


@router.delete("/draft")
def dismiss_draft(owner: Owner = Depends(current_owner), db: Session = Depends(get_db)):
    # A2: the owner keeps their own profile; the version does not change.
    p = get_profile(db, owner.id)
    p.pending_draft, p.pending_claims, p.pending_unsupported_claims = None, None, None
    db.commit()
    return profile_out(p)
