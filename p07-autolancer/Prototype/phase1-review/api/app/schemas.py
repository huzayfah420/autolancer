"""Pydantic models: request validation, AI output contracts and fixed option lists."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---- Fixed option lists (served to the hub by GET /options) ----

SERVICES = ["finance", "software", "data", "research", "writing"]

# Actions the policy can allow. Phase 1 enforces the first two; submit_proposals only
# feeds the pursue-eligible flag until proposals exist in Phase 2.
ALLOWED_ACTIONS = {
    "discover_jobs": "Fetch jobs from the marketplace",
    "assess_jobs": "Spend AI budget assessing jobs",
    "submit_proposals": "Submit proposals automatically (makes jobs pursue-eligible)",
}

# Conditions that hold an otherwise-pursuable job for owner review.
REVIEW_CONDITIONS = {
    "high_uncertainty": "Hold jobs where the AI's uncertainty is high",
    "finance_jobs": "Hold every finance job for review",
    "short_deadline": "Hold jobs due in under 3 days",
}

Category = Literal["finance", "software", "data", "research", "writing", "other"]


# ---- Profile ----

class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["link", "text"]
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def link_must_be_url(self):
        if self.kind == "link" and not self.content.startswith(("http://", "https://")):
            raise ValueError("A link must start with http:// or https://")
        return self


class ProfileIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    services: list[Literal["finance", "software", "data", "research", "writing"]] = Field(max_length=5)
    skills_summary: str = Field(default="", max_length=3000)
    evidence: list[Evidence] = Field(default_factory=list, max_length=20)

    @field_validator("services")
    @classmethod
    def unique_services(cls, v):
        return sorted(set(v))


# ---- Policy ----

class PolicyIn(BaseModel):
    """A new policy version. Anything invalid is rejected with 422 and nothing is saved."""

    model_config = ConfigDict(extra="forbid")
    allowed_actions: list[str] = Field(max_length=len(ALLOWED_ACTIONS))
    max_bid: float = Field(gt=0, le=1_000_000)
    daily_proposal_limit: int = Field(ge=0, le=100)
    workload_limit: int = Field(ge=0, le=20)
    daily_ai_cap_usd: float = Field(ge=0, le=100)
    review_conditions: list[str] = Field(default_factory=list, max_length=len(REVIEW_CONDITIONS))
    min_job_budget: float = Field(ge=0, le=1_000_000)
    excluded_keywords: list[str] = Field(default_factory=list, max_length=50)
    # Deadline limit (FR-004): jobs due sooner than this are declined. 0 = no limit.
    min_deadline_days: int = Field(default=0, ge=0, le=365)

    @field_validator("allowed_actions")
    @classmethod
    def known_actions(cls, v):
        bad = [a for a in v if a not in ALLOWED_ACTIONS]
        if bad:
            raise ValueError(f"Unknown actions: {', '.join(bad)}")
        return sorted(set(v))

    @field_validator("review_conditions")
    @classmethod
    def known_conditions(cls, v):
        bad = [c for c in v if c not in REVIEW_CONDITIONS]
        if bad:
            raise ValueError(f"Unknown review conditions: {', '.join(bad)}")
        return sorted(set(v))

    @field_validator("excluded_keywords")
    @classmethod
    def clean_keywords(cls, v):
        out = []
        for kw in v:
            kw = kw.strip().lower()
            if not kw:
                raise ValueError("Excluded keywords cannot be blank")
            if len(kw) > 50:
                raise ValueError("Excluded keywords must be 50 characters or fewer")
            if kw not in out:
                out.append(kw)
        return out


# ---- Connections ----

class ConnectionToggle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


# ---- AI output contracts (validated; anything else = invalid output) ----

class DraftClaim(BaseModel):
    """One claim made in the draft and the evidence items (E1, E2, ...) that support it."""

    text: str = Field(min_length=1, max_length=300)
    evidence_ids: list[str] = Field(min_length=1, max_length=10)


class AIProfileDraft(BaseModel):
    """Output of "Draft my profile" (AIR-002, FR-003 AC-1: claims link to their evidence)."""

    draft: str = Field(min_length=1, max_length=4000)
    claims: list[DraftClaim] = Field(default_factory=list, max_length=20)
    unsupported_claims: list[str] = Field(default_factory=list, max_length=20)


class AIAssessment(BaseModel):
    """Output of a job assessment (AIR-001). The rules in rules.py turn it into a class."""

    category: Category
    fit: float = Field(ge=0, le=1)
    fit_reasons: list[str] = Field(min_length=1, max_length=6)
    deliverables: list[str] = Field(default_factory=list, max_length=10)
    effort_hours_min: float = Field(gt=0, le=2000)
    effort_hours_max: float = Field(gt=0, le=2000)
    price_min: float = Field(ge=0, le=1_000_000)
    price_max: float = Field(ge=0, le=1_000_000)
    uncertainty: Literal["low", "medium", "high"]
    open_questions: list[str] = Field(default_factory=list, max_length=10)
    # Things the estimates take for granted, and why the job is (or is not) worth the money.
    assumptions: list[str] = Field(default_factory=list, max_length=10)
    expected_return_basis: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def ranges_ordered(self):
        if self.effort_hours_max < self.effort_hours_min:
            raise ValueError("effort_hours_max must be >= effort_hours_min")
        if self.price_max < self.price_min:
            raise ValueError("price_max must be >= price_min")
        return self
