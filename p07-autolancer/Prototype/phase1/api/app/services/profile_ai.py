"""The "Draft my profile" feature (row 4, UC-001 step 5, FR-003, AIR-002).

One LLM call returning {draft, claims[], unsupported_claims[]}. Each claim must cite the
evidence items (E1, E2, ...) that support it; the application checks those citations.
The draft is stored as pending and only replaces the owner's summary if they accept it.
"""

import json

from ..models import Profile
from ..schemas import AIProfileDraft

SYSTEM_PROMPT = (
    "You write a short freelancer profile for the owner of an autonomous freelancing service. "
    "Use ONLY facts found in the owner's services, skills summary and evidence items. "
    "Do not invent clients, years of experience, credentials, numbers or results. "
    "List every claim the draft makes in `claims`, each with the ids (E1, E2, ...) of the evidence "
    "items that support it. Leave out of the draft any service or claim that no evidence item "
    "supports, and list each such claim in unsupported_claims so the owner can add evidence. "
    "Keep the draft under 150 words."
)


def evidence_ids(profile: Profile) -> list[str]:
    """Stable ids for the evidence items, in profile order: E1, E2, ..."""
    return [f"E{i + 1}" for i in range(len(profile.evidence))]


def build_input(profile: Profile) -> str:
    evidence = [{"id": eid, **e} for eid, e in zip(evidence_ids(profile), profile.evidence)]
    return json.dumps(
        {"services": profile.services, "skills_summary": profile.skills_summary, "evidence": evidence},
        indent=1,
    )


def mock_draft(profile: Profile) -> dict:
    """Deterministic stand-in: a service counts as supported if some evidence mentions it."""
    ids = evidence_ids(profile)
    claims, unsupported = [], []
    for s in profile.services:
        cited = [eid for eid, e in zip(ids, profile.evidence) if s in f"{e['title']} {e['content']}".lower()]
        if cited:
            claims.append({"text": f"Delivers {s} work", "evidence_ids": cited})
        else:
            unsupported.append(f"No evidence provided for {s} work")
    if claims:
        supported = [c["text"].removeprefix("Delivers ").removesuffix(" work") for c in claims]
        titles = ", ".join(e["title"] for e in profile.evidence[:3])
        draft = f"I deliver {', '.join(supported)} work for small and medium businesses. Recent work: {titles}."
    else:
        draft = "Add evidence of past work so a grounded profile can be drafted."
    return {"draft": draft, "claims": claims, "unsupported_claims": unsupported}


def ground_claims(result: AIProfileDraft, profile: Profile) -> tuple[list[dict], list[str]]:
    """Application check on the model's citations (generated text cannot vouch for itself).

    Unknown evidence ids are dropped; a claim left with no real evidence becomes unsupported.
    """
    valid = set(evidence_ids(profile))
    claims, unsupported = [], list(result.unsupported_claims)
    for c in result.claims:
        cited = [eid for eid in dict.fromkeys(c.evidence_ids) if eid in valid]
        if cited:
            claims.append({"text": c.text, "evidence_ids": cited})
        elif c.text not in unsupported:
            unsupported.append(c.text)
    return claims, unsupported


def draft_args(profile: Profile):
    """Arguments for llm.complete_json, kept here so the router stays thin."""
    return SYSTEM_PROMPT, build_input(profile), AIProfileDraft, lambda: mock_draft(profile)
