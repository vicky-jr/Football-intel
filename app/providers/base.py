"""Provider-neutral models and adapter contract for market discovery.

Adapters must preserve unfamiliar source markets instead of dropping them.
"""
from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence


@dataclass(frozen=True)
class ProviderEvent:
    provider: str
    source_event_id: str
    sport: str
    competition: str | None
    name: str
    start_time: str | None
    status: str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderSelection:
    source_selection_id: str | None
    name: str
    odds_decimal: float | None
    participant: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderMarket:
    provider: str
    source_event_id: str
    source_market_id: str | None
    name: str
    period: str | None
    line: str | float | None
    status: str | None
    selections: Sequence[ProviderSelection]
    source_updated_at: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    classified: bool = False


class OddsProvider(Protocol):
    """Contract every bookmaker or odds-aggregator adapter must implement."""

    provider_id: str

    async def list_books(self) -> list[dict[str, Any]]:
        """Return bookmakers visible to this provider account."""
        ...

    async def list_sports(self) -> list[dict[str, Any]]:
        """Return sports with available odds coverage."""
        ...

    async def list_competitions(self, sport_id: str) -> list[dict[str, Any]]:
        """Return competitions and their market-family availability flags."""
        ...

    async def list_events(self, competition_id: str, date: str) -> list[ProviderEvent]:
        """Return scheduled events for a competition and date."""
        ...

    async def get_event_markets(
        self, event: ProviderEvent, package: str
    ) -> list[ProviderMarket]:
        """Return every market instance and outcome exposed for this event/package.

        Unknown market types must still be returned with classified=False.
        """
        ...
