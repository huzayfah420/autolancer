"""Marketplace adapter. The API reaches the simulator only through this HTTP client,
so a real marketplace adapter with the same two methods can replace it later.
"""

import httpx
from pydantic import BaseModel, Field, ValidationError

from .config import get_settings


class MarketplaceError(Exception):
    """The marketplace could not be reached or answered with something unusable."""


class SourceClient(BaseModel):
    name: str = ""
    country: str = ""
    rating: float | None = None


class SourceListing(BaseModel):
    """Shape every adapter must return for a listing."""

    id: str = Field(min_length=1, max_length=100)
    title: str
    description: str
    category: str
    budget_min: float = Field(ge=0)
    budget_max: float = Field(ge=0)
    currency: str = "USD"
    deadline_days: int = Field(ge=0)
    skills: list[str] = Field(default_factory=list)
    client: SourceClient = Field(default_factory=SourceClient)
    url: str = ""
    posted_at: str = ""


class Capabilities(BaseModel):
    name: str
    account: str
    simulated: bool
    operations: list[str]


class SimulatorAdapter:
    provider = "simulator"

    def __init__(self, client: httpx.Client):
        self.client = client

    def _get(self, path: str):
        try:
            resp = self.client.get(path)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise MarketplaceError(f"Marketplace returned HTTP {e.response.status_code}")
        except (httpx.HTTPError, ValueError) as e:
            raise MarketplaceError(f"Marketplace unreachable: {type(e).__name__}")

    def capabilities(self) -> Capabilities:
        try:
            return Capabilities.model_validate(self._get("/capabilities"))
        except ValidationError:
            raise MarketplaceError("Marketplace sent an invalid capabilities response")

    def list_listings(self) -> list[SourceListing]:
        data = self._get("/listings")
        try:
            return [SourceListing.model_validate(item) for item in data["listings"]]
        except (KeyError, TypeError, ValidationError):
            raise MarketplaceError("Marketplace sent an invalid listings response")


def get_marketplace():
    """FastAPI dependency. Tests override it to point at the in-process simulator."""
    with httpx.Client(base_url=get_settings().simulator_url, timeout=10) as client:
        yield SimulatorAdapter(client)
