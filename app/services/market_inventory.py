"""Loss-aware in-memory market inventory and coverage snapshots.

This is the first storage boundary for provider data. It preserves source
market/selection objects—including unclassified markets—without inventing
normalised market definitions or probabilities.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from app.providers.base import ProviderEvent, ProviderMarket


@dataclass(frozen=True)
class EventMarketSnapshot:
    provider: str
    source_event_id: str
    captured_at: datetime
    markets: tuple[ProviderMarket, ...]


class MarketInventory:
    """Store timestamped event-market snapshots in memory.

    Production persistence (for example PostgreSQL) can implement the same
    boundary later without changing provider adapters.
    """

    def __init__(self) -> None:
        self._events: dict[tuple[str, str], ProviderEvent] = {}
        self._snapshots: list[EventMarketSnapshot] = []

    def record_event(self, event: ProviderEvent) -> None:
        if not event.provider.strip() or not event.source_event_id.strip():
            raise ValueError("event provider and source_event_id are required")
        self._events[(event.provider.lower(), event.source_event_id)] = event

    def record_markets(
        self,
        event: ProviderEvent,
        markets: Iterable[ProviderMarket],
        captured_at: datetime | None = None,
    ) -> EventMarketSnapshot:
        key = (event.provider.lower(), event.source_event_id)
        if key not in self._events:
            raise KeyError("record the event before recording its markets")

        preserved = tuple(markets)
        for market in preserved:
            if market.provider.lower() != event.provider.lower():
                raise ValueError("market provider does not match its event")
            if market.source_event_id != event.source_event_id:
                raise ValueError("market source_event_id does not match its event")

        timestamp = captured_at or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")

        snapshot = EventMarketSnapshot(
            provider=event.provider,
            source_event_id=event.source_event_id,
            captured_at=timestamp,
            markets=preserved,
        )
        self._snapshots.append(snapshot)
        return snapshot

    def snapshots_for_event(
        self, provider: str, source_event_id: str
    ) -> list[EventMarketSnapshot]:
        return [
            snapshot for snapshot in self._snapshots
            if snapshot.provider.lower() == provider.lower()
            and snapshot.source_event_id == source_event_id
        ]

    def coverage_report(self) -> dict[str, object]:
        by_provider: dict[str, dict[str, int | str | None]] = {}
        for snapshot in self._snapshots:
            provider = snapshot.provider
            stats = by_provider.setdefault(
                provider,
                {
                    "events_scanned": 0,
                    "snapshots": 0,
                    "markets_received": 0,
                    "selections_received": 0,
                    "unclassified_markets": 0,
                    "last_captured_at": None,
                },
            )
            stats["snapshots"] = int(stats["snapshots"]) + 1
            stats["markets_received"] = int(stats["markets_received"]) + len(snapshot.markets)
            stats["selections_received"] = int(stats["selections_received"]) + sum(
                len(market.selections) for market in snapshot.markets
            )
            stats["unclassified_markets"] = int(stats["unclassified_markets"]) + sum(
                not market.classified for market in snapshot.markets
            )
            stats["last_captured_at"] = snapshot.captured_at.isoformat()
        for provider, stats in by_provider.items():
            stats["events_scanned"] = len({
                snapshot.source_event_id for snapshot in self._snapshots
                if snapshot.provider == provider
            })
        return {"providers": by_provider, "snapshot_count": len(self._snapshots)}
