"""Deterministic application rules (row 8, UC-002 steps 5-6, FR-006).

The AI only estimates; these rules decide pursue / clarify / decline, compute the rank
score and the pursue-eligible flag. Generated text can never make a job eligible.
"""

from dataclasses import dataclass, field

from .models import Listing, PolicyVersion, Profile
from .schemas import AIAssessment

# Rank score weights (sum to 1). Score is reported on a 0-100 scale.
WEIGHTS = {"fit": 0.40, "effort": 0.15, "deadline": 0.20, "price": 0.25}
HOURS_PER_DAY = 6  # owner capacity used for deadline feasibility
MAX_EFFORT_HOURS = 160  # effort at or above this scores 0
DECLINE_FIT, CLARIFY_FIT = 0.4, 0.6
SHORT_DEADLINE_DAYS = 3


@dataclass
class RuleResult:
    classification: str  # "pursue" | "clarify" | "decline"
    score: float
    breakdown: dict
    pursue_eligible: bool
    reasons: list[str] = field(default_factory=list)


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def matches_keyword(title: str, description: str, skills: list[str], keywords: list[str]) -> str | None:
    """First excluded keyword found in the job text (case-insensitive), else None."""
    text = f"{title} {description} {' '.join(skills)}".lower()
    return next((kw for kw in keywords if kw in text), None)


def score(listing: Listing, ai: AIAssessment, policy: PolicyVersion) -> dict:
    """Weighted score from fit, effort, deadline slack and price (each 0..1)."""
    available = listing.deadline_days * HOURS_PER_DAY
    price_mid = min((ai.price_min + ai.price_max) / 2, listing.budget_max)
    parts = {
        "fit": ai.fit,
        "effort": 1 - _clamp(ai.effort_hours_max / MAX_EFFORT_HOURS),
        "deadline": _clamp((available - ai.effort_hours_max) / available) if available > 0 else 0.0,
        "price": _clamp(price_mid / policy.max_bid),
    }
    parts = {k: round(v, 3) for k, v in parts.items()}
    total = round(100 * sum(WEIGHTS[k] * v for k, v in parts.items()), 1)
    return {"parts": parts, "weights": WEIGHTS, "total": total}


def classify(listing: Listing, ai: AIAssessment, profile: Profile, policy: PolicyVersion) -> RuleResult:
    breakdown = score(listing, ai, policy)
    reasons: list[str] = []

    # Decline: unsupported service, poor fit, policy filters, or infeasible deadline.
    decline = []
    if ai.category not in profile.services:
        decline.append(f"'{ai.category}' is not one of your services")
    if ai.fit < DECLINE_FIT:
        decline.append(f"Fit {ai.fit:.2f} is below {DECLINE_FIT}")
    if listing.budget_max < policy.min_job_budget:
        decline.append(f"Budget {listing.budget_max:.0f} is below your minimum {policy.min_job_budget:.0f}")
    if kw := matches_keyword(listing.title, listing.description, listing.skills, policy.excluded_keywords):
        decline.append(f"Matches excluded keyword '{kw}'")
    if ai.effort_hours_min > listing.deadline_days * HOURS_PER_DAY:
        decline.append(
            f"Needs at least {ai.effort_hours_min:.0f}h but only {listing.deadline_days * HOURS_PER_DAY}h available before the deadline"
        )
    if decline:
        return RuleResult("decline", breakdown["total"], breakdown, False, decline)

    # Clarify: the job may suit, but something must be answered first.
    clarify = []
    if ai.open_questions:
        clarify.append(f"{len(ai.open_questions)} open question(s) for the client")
    if ai.uncertainty == "high":
        clarify.append("AI uncertainty is high")
    if ai.fit < CLARIFY_FIT:
        clarify.append(f"Fit {ai.fit:.2f} is borderline")
    if clarify:
        return RuleResult("clarify", breakdown["total"], breakdown, False, clarify)

    # Pursue: now check whether policy lets the system pursue it without the owner.
    reasons.append("Supported service with good fit and a feasible deadline")
    blockers = []
    if "submit_proposals" not in policy.allowed_actions:
        blockers.append("Policy does not allow submitting proposals")
    if policy.daily_proposal_limit == 0:
        blockers.append("Daily proposal limit is 0")
    if policy.workload_limit == 0:
        blockers.append("Workload limit is 0")
    if ai.price_min > policy.max_bid:
        blockers.append(f"Lowest sensible price {ai.price_min:.0f} exceeds max bid {policy.max_bid:.0f}")
    if "high_uncertainty" in policy.review_conditions and ai.uncertainty == "high":
        blockers.append("Review required: high uncertainty")
    if "finance_jobs" in policy.review_conditions and ai.category == "finance":
        blockers.append("Review required: finance job")
    if "short_deadline" in policy.review_conditions and listing.deadline_days < SHORT_DEADLINE_DAYS:
        blockers.append(f"Review required: deadline under {SHORT_DEADLINE_DAYS} days")
    return RuleResult("pursue", breakdown["total"], breakdown, not blockers, reasons + blockers)
