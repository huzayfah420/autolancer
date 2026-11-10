"""Marketplace adapter. The API reaches the simulator only through this HTTP client,
so a real marketplace adapter with the same two methods can replace it later.
"""

import httpx
from pydantic import BaseModel, Field, ValidationError

from .config import get_settings


class MarketplaceError(Exception):
    """The marketplace could not be reached or answered with something unusable.

    `retryable` is True for outages and rate limits (network errors, HTTP 5xx and 429),
    where trying again soon may work; False for answers that will not change on retry.
    """

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


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
            code = e.response.status_code
            raise MarketplaceError(f"Marketplace returned HTTP {code}", retryable=code >= 500 or code == 429)
        except httpx.HTTPError as e:
            raise MarketplaceError(f"Marketplace unreachable: {type(e).__name__}", retryable=True)
        except ValueError:
            raise MarketplaceError("Marketplace sent a response that is not JSON")

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
