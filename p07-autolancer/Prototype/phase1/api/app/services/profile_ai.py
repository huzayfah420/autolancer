"""The "Draft my profile" feature (row 4, UC-001 step 5, FR-003, AIR-002).

One LLM call returning {draft, unsupported_claims[]}. The draft is stored as pending
and only replaces the owner's summary if they accept it.
"""

import json

from ..models import Profile
from ..schemas import AIProfileDraft

SYSTEM_PROMPT = (
    "You write a short freelancer profile for the owner of an autonomous freelancing service. "
    "Use ONLY facts found in the owner's services, skills summary and evidence items. "
    "Do not invent clients, years of experience, credentials, numbers or results. "
    "Leave out of the draft any service or claim that no evidence item supports, and list each "
    "such claim in unsupported_claims so the owner can add evidence. Keep the draft under 150 words."
)


def build_input(profile: Profile) -> str:
    return json.dumps(
        {"services": profile.services, "skills_summary": profile.skills_summary, "evidence": profile.evidence},
        indent=1,
    )


def mock_draft(profile: Profile) -> dict:
    """Deterministic stand-in: a service counts as supported if some evidence mentions it."""
    evidence_text = " ".join(f"{e['title']} {e['content']}" for e in profile.evidence).lower()
    supported = [s for s in profile.services if s in evidence_text]
    unsupported = [f"No evidence provided for {s} work" for s in profile.services if s not in evidence_text]
    if supported:
        titles = ", ".join(e["title"] for e in profile.evidence[:3])
        draft = f"I deliver {', '.join(supported)} work for small and medium businesses. Recent work: {titles}."
    else:
        draft = "Add evidence of past work so a grounded profile can be drafted."
    return {"draft": draft, "unsupported_claims": unsupported}


def draft_args(profile: Profile):
    """Arguments for llm.complete_json, kept here so the router stays thin."""
    return SYSTEM_PROMPT, build_input(profile), AIProfileDraft, lambda: mock_draft(profile)
