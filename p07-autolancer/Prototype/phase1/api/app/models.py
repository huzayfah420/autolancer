"""SQLAlchemy tables. Every table has owner_id and every query filters on it.

Tables: profiles, policy_versions, connections, listings, assessments, ai_usage.
Money is stored as Float to keep the prototype simple (no Decimal-as-string JSON).
"""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Profile(Base):
    """One row per owner. `version` goes up on every accepted change."""

    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    services: Mapped[list] = mapped_column(JSON, default=list)
    skills_summary: Mapped[str] = mapped_column(Text, default="")
    # Each item: {"kind": "link" | "text", "title": str, "content": str}
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    # Last AI draft, kept until the owner accepts or dismisses it (UC-001 E3).
    pending_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    pending_unsupported_claims: Mapped[list | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PolicyVersion(Base):
    """Append-only. The highest version for an owner is the active policy."""

    __tablename__ = "policy_versions"
    __table_args__ = (UniqueConstraint("owner_id", "version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    version: Mapped[int] = mapped_column(Integer)
    allowed_actions: Mapped[list] = mapped_column(JSON)
    max_bid: Mapped[float] = mapped_column(Float)
    daily_proposal_limit: Mapped[int] = mapped_column(Integer)
    workload_limit: Mapped[int] = mapped_column(Integer)
    daily_ai_cap_usd: Mapped[float] = mapped_column(Float)
    review_conditions: Mapped[list] = mapped_column(JSON)
    min_job_budget: Mapped[float] = mapped_column(Float)
    excluded_keywords: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Connection(Base):
    """Marketplace connection state plus the last fetch outcome."""

    __tablename__ = "connections"
    __table_args__ = (UniqueConstraint("owner_id", "provider"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    provider: Mapped[str] = mapped_column(String(40))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    # "disconnected" | "connected" | "unavailable"
    status: Mapped[str] = mapped_column(String(20), default="disconnected")
    account_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    operations: Mapped[list] = mapped_column(JSON, default=list)
    status_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Fetch bookkeeping: last_fetch_at only moves on success (UC-002 E1).
    last_fetch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_fetch_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_fetch_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class Listing(Base):
    """A job from the marketplace, de-duplicated on (owner, source, source_id)."""

    __tablename__ = "listings"
    __table_args__ = (UniqueConstraint("owner_id", "source", "source_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    source: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[str] = mapped_column(String(100))
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(40))
    budget_min: Mapped[float] = mapped_column(Float)
    budget_max: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    deadline_days: Mapped[int] = mapped_column(Integer)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    # Client identity is stored for display only and never sent to the AI (AIR-001 fairness).
    client: Mapped[dict] = mapped_column(JSON, default=dict)
    url: Mapped[str] = mapped_column(String(500), default="")
    posted_at: Mapped[str] = mapped_column(String(40), default="")
    # Hash of the job content; a different hash on fetch means a new listing version.
    content_hash: Mapped[str] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Assessment(Base):
    """One row per assessment attempt. The newest row per listing is its status.

    It is "current" only if its listing/profile/policy versions match the live ones.
    """

    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    listing_version: Mapped[int] = mapped_column(Integer)
    profile_version: Mapped[int] = mapped_column(Integer)
    policy_version: Mapped[int] = mapped_column(Integer)
    # "assessed" | "unassessed"
    status: Mapped[str] = mapped_column(String(20))
    unassessed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Validated AI output (see schemas.AIAssessment); null when unassessed.
    ai_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Rule outputs (see rules.py).
    classification: Mapped[str | None] = mapped_column(String(20), nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pursue_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    rule_reasons: Mapped[list] = mapped_column(JSON, default=list)
    # True when only the policy changed and the earlier AI output was reused (UC-002 A1).
    reused_ai_output: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AIUsage(Base):
    """Cost ledger: one row per model call, successful or not."""

    __tablename__ = "ai_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    day: Mapped[date] = mapped_column(Date, index=True)  # UTC day, used for the daily cap
    purpose: Mapped[str] = mapped_column(String(40))  # "assessment" | "profile_draft"
    listing_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model: Mapped[str] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
