"""Autonomy policy (row 5, UC-001 steps 6-7, E3, FR-004).

Policies are append-only: each valid save inserts a new version and the newest is active.
Invalid input fails Pydantic validation (422) and nothing is written.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import Owner, current_owner
from ..db import get_db
from ..models import PolicyVersion
from ..schemas import PolicyIn
from ..services.common import active_policy

router = APIRouter(prefix="/policy", tags=["policy"])


def policy_out(p: PolicyVersion) -> dict:
    return {
        "version": p.version,
        "created_at": p.created_at,
        **{f: getattr(p, f) for f in PolicyIn.model_fields},
    }


@router.get("")
def read_policy(owner: Owner = Depends(current_owner), db: Session = Depends(get_db)):
    history = db.scalars(
        select(PolicyVersion).where(PolicyVersion.owner_id == owner.id).order_by(PolicyVersion.version.desc())
    ).all()
    return {"active": policy_out(history[0]) if history else None, "history": [policy_out(p) for p in history]}


@router.post("", status_code=201)
def save_policy(body: PolicyIn, owner: Owner = Depends(current_owner), db: Session = Depends(get_db)):
    current = active_policy(db, owner.id)
    row = PolicyVersion(owner_id=owner.id, version=(current.version + 1 if current else 1), **body.model_dump())
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # Two saves raced for the same version number; nothing was written for this one.
        db.rollback()
        raise HTTPException(409, "The policy changed while you were saving. Reload and try again.")
    return policy_out(row)
