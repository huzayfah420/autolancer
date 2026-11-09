"""Owner-scoped lookups shared by several routers and services."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..llm import Usage
from ..models import AIUsage, Connection, PolicyVersion, Profile

SIMULATOR = "simulator"


def utc_today():
    return datetime.now(timezone.utc).date()


def get_profile(db: Session, owner_id: uuid.UUID) -> Profile:
    """The owner's profile, created empty (version 1) on first access."""
    profile = db.scalar(select(Profile).where(Profile.owner_id == owner_id))
    if profile is None:
        profile = Profile(owner_id=owner_id, version=1, services=[], skills_summary="", evidence=[])
        db.add(profile)
        db.commit()
    return profile


def active_policy(db: Session, owner_id: uuid.UUID) -> PolicyVersion | None:
    """Newest policy version = active policy."""
    return db.scalar(
        select(PolicyVersion).where(PolicyVersion.owner_id == owner_id).order_by(PolicyVersion.version.desc()).limit(1)
    )


def get_connection(db: Session, owner_id: uuid.UUID) -> Connection:
    """The simulator connection row, created disconnected on first access (UC-001 A1)."""
    conn = db.scalar(select(Connection).where(Connection.owner_id == owner_id, Connection.provider == SIMULATOR))
    if conn is None:
        conn = Connection(owner_id=owner_id, provider=SIMULATOR, enabled=False, status="disconnected", operations=[])
        db.add(conn)
        db.commit()
    return conn


def daily_cap(db: Session, owner_id: uuid.UUID) -> float:
    policy = active_policy(db, owner_id)
    return policy.daily_ai_cap_usd if policy else get_settings().default_daily_ai_cap_usd


def spent_today(db: Session, owner_id: uuid.UUID) -> float:
    total = db.scalar(
        select(func.coalesce(func.sum(AIUsage.cost_usd), 0.0)).where(
            AIUsage.owner_id == owner_id, AIUsage.day == utc_today()
        )
    )
    return float(total or 0.0)


def cap_reached(db: Session, owner_id: uuid.UUID) -> bool:
    return spent_today(db, owner_id) >= daily_cap(db, owner_id)


def record_usage(
    db: Session,
    owner_id: uuid.UUID,
    purpose: str,
    usage: Usage,
    ok: bool,
    error: str | None = None,
    listing_id: int | None = None,
) -> None:
    """Write one cost-ledger row. Committed by the caller."""
    db.add(
        AIUsage(
            owner_id=owner_id,
            day=utc_today(),
            purpose=purpose,
            listing_id=listing_id,
            model=usage.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cost_usd=usage.cost_usd,
            ok=ok,
            error=error,
        )
    )
