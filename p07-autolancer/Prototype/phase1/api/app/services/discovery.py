"""Fetch jobs on demand (row 6, UC-002 steps 1-2 and E1, FR-005)."""

import hashlib
import json
import time
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..marketplace import MarketplaceError, SimulatorAdapter, SourceListing
from ..models import Listing, utcnow
from ..rules import matches_keyword
from .common import active_policy, get_connection


class PreconditionError(Exception):
    """The action cannot run yet; the message tells the owner what to do."""


# Bounded retry (UC-002 E1): wait this long before each extra attempt, so at most 3 attempts.
RETRY_DELAYS_SECONDS = (1.0, 2.0)


class FetchFailed(Exception):
    """Every allowed attempt failed; carries the last error and how many attempts were made."""

    def __init__(self, error: MarketplaceError, attempts: int):
        self.error, self.attempts = error, attempts


def _list_with_retry(market: SimulatorAdapter) -> tuple[list[SourceListing], int]:
    """Fetch listings, retrying only failures that may pass (outage, rate limit)."""
    delays = [0.0, *RETRY_DELAYS_SECONDS]
    for attempt, delay in enumerate(delays, start=1):
        time.sleep(delay)
        try:
            return market.list_listings(), attempt
        except MarketplaceError as e:
            if not e.retryable or attempt == len(delays):
                raise FetchFailed(e, attempt)
    raise AssertionError("unreachable")


CONTENT_FIELDS = ("title", "description", "category", "budget_min", "budget_max", "currency", "deadline_days", "skills")


def content_hash(item: SourceListing) -> str:
    """Hash of the fields that matter for assessment; a change bumps the listing version."""
    data = {f: getattr(item, f) for f in CONTENT_FIELDS}
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def require_marketplace(db: Session, owner_id: uuid.UUID, operation: str):
    """Stop the action unless the connection is enabled and supports the operation (FR-002 AC-2)."""
    conn = get_connection(db, owner_id)
    if not conn.enabled or conn.status != "connected":
        raise PreconditionError("The Marketplace Simulator is not connected. Connect it on the Connections page.")
    if operation not in conn.operations:
        raise PreconditionError(f"The marketplace does not support '{operation}'. Reconnect or handle it manually.")
    return conn


def fetch_jobs(db: Session, owner_id: uuid.UUID, market: SimulatorAdapter) -> dict:
    conn = require_marketplace(db, owner_id, "list_listings")
    policy = active_policy(db, owner_id)
    if policy is None:
        raise PreconditionError("Save a policy first: the job filters come from it.")
    if "discover_jobs" not in policy.allowed_actions:
        raise PreconditionError("Your policy does not allow job discovery.")

    now = utcnow()
    conn.last_fetch_attempt_at = now
    try:
        items, attempts = _list_with_retry(market)
    except FetchFailed as e:
        # E1: keep every stored listing and the old last_fetch_at; record the failure and retry status.
        conn.last_fetch_error = str(e.error)
        conn.last_fetch_attempts = e.attempts
        db.commit()
        return {"ok": False, "error": str(e.error), "attempts": e.attempts, "last_fetch_at": conn.last_fetch_at}

    counts = {"new": 0, "changed": 0, "unchanged": 0, "filtered_out": 0}
    for item in items:
        # Job filters from the active policy.
        if item.budget_max < policy.min_job_budget or matches_keyword(
            item.title, item.description, item.skills, policy.excluded_keywords
        ):
            counts["filtered_out"] += 1
            continue

        fields = item.model_dump(exclude={"id"})
        digest = content_hash(item)
        existing = db.scalar(
            select(Listing).where(
                Listing.owner_id == owner_id, Listing.source == market.provider, Listing.source_id == item.id
            )
        )
        if existing is None:
            db.add(
                Listing(
                    owner_id=owner_id, source=market.provider, source_id=item.id, simulated=True,
                    content_hash=digest, version=1, first_seen_at=now, changed_at=now, last_seen_at=now, **fields,
                )
            )
            counts["new"] += 1
        elif existing.content_hash != digest:
            for k, v in fields.items():
                setattr(existing, k, v)
            existing.content_hash = digest
            existing.version += 1  # makes the old assessment stale (row 8)
            existing.changed_at = now
            existing.last_seen_at = now
            counts["changed"] += 1
        else:
            existing.last_seen_at = now
            counts["unchanged"] += 1

    conn.last_fetch_at = now
    conn.last_fetch_error = None
    conn.last_fetch_attempts = attempts
    db.commit()
    return {"ok": True, "error": None, "attempts": attempts, "last_fetch_at": now, **counts}
