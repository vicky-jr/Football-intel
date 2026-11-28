"""Provider-neutral orchestration for bounded market-discovery scans.

This first implementation is intentionally in-memory: it exercises the provider
contract and preserves every returned market, while durable persistence is a
separate roadmap step. Provider adapters are responsible for exhausting their
permitted pagination and reporting only data their account may access.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, TypeVar

from app.providers.base import OddsProvider, ProviderEvent
from app.providers.registry import ProviderRegistry
from app.services.market_inventory import MarketInventory

T = TypeVar("T")


@dataclass(frozen=True)
class ScanFailure:
    stage: str
    scope: str
    message: str


@dataclass
class IngestionReport:
    provider: str
    scan_date: str
    started_at: datetime
    completed_at: datetime | None = None
    books_discovered: int = 0
    sports_discovered: int = 0
    competitions_discovered: int = 0
    events_discovered: int = 0
    events_scanned: int = 0
    market_snapshots_recorded: int = 0
    markets_received: int = 0
    selections_received: int = 0
    failures: list[ScanFailure] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return self.completed_at is not None and not self.failures


class IngestionOrchestrator:
    """Run a bounded, failure-isolated discovery scan for one registered provider."""

    def __init__(
        self,
        registry: ProviderRegistry,
        inventory: MarketInventory,
        *,
        max_concurrency: int = 8,
        max_retries: int = 2,
        retry_delay_seconds: float = 0.0,
    ) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds cannot be negative")
        self.registry = registry
        self.inventory = inventory
        self.max_concurrency = max_concurrency
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

    async def _retry(self, operation: Callable[[], Awaitable[T]]) -> T:
        for attempt in range(self.max_retries + 1):
            try:
                return await operation()
            except Exception:
                if attempt >= self.max_retries:
                    raise
                if self.retry_delay_seconds:
                    await asyncio.sleep(self.retry_delay_seconds * (2 ** attempt))
        raise RuntimeError("unreachable retry state")

    @staticmethod
    def _source_id(item: dict[str, Any], *, scope: str) -> str:
        value = item.get("id") or item.get("source_id")
        if value is None or not str(value).strip():
            raise ValueError(f"{scope} item is missing an id")
        return str(value)

    async def scan(
        self,
        provider_id: str,
        scan_date: str,
        *,
        package: str = "default",
    ) -> IngestionReport:
        provider: OddsProvider = self.registry.get(provider_id)
        started = datetime.now(timezone.utc)
        report = IngestionReport(
            provider=provider.provider_id,
            scan_date=scan_date,
            started_at=started,
        )

        async def discover(stage: str, scope: str, operation: Callable[[], Awaitable[T]]) -> T | None:
            try:
                return await self._retry(operation)
            except Exception as exc:
                report.failures.append(ScanFailure(stage, scope, f"{type(exc).__name__}: {exc}"))
                return None

        books = await discover("books", provider.provider_id, provider.list_books)
        if books is not None:
            report.books_discovered = len(books)

        sports = await discover("sports", provider.provider_id, provider.list_sports)
        if sports is not None:
            report.sports_discovered = len(sports)

        if sports is None:
            report.completed_at = datetime.now(timezone.utc)
            return report

        competitions: list[tuple[str, str]] = []
        for sport in sports:
            try:
                sport_id = self._source_id(sport, scope="sport")
            except ValueError as exc:
                report.failures.append(ScanFailure("competitions", "unknown-sport", str(exc)))
                continue
            items = await discover(
                "competitions",
                sport_id,
                lambda sport_id=sport_id: provider.list_competitions(sport_id),
            )
            if items is None:
                continue
            for item in items:
                try:
                    competitions.append((sport_id, self._source_id(item, scope="competition")))
                except ValueError as exc:
                    report.failures.append(ScanFailure("events", sport_id, str(exc)))

        report.competitions_discovered = len(competitions)
        events_by_key: dict[tuple[str, str], ProviderEvent] = {}
        for sport_id, competition_id in competitions:
            events = await discover(
                "events",
                competition_id,
                lambda competition_id=competition_id: provider.list_events(
                    competition_id, scan_date
                ),
            )
            if events is None:
                continue
            for event in events:
                if event.provider.strip().lower() != provider.provider_id.strip().lower():
                    report.failures.append(
                        ScanFailure("events", competition_id, "event provider does not match adapter")
                    )
                    continue
                key = (event.provider.lower(), event.source_event_id)
                events_by_key[key] = event

        report.events_discovered = len(events_by_key)
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def scan_event(event: ProviderEvent) -> None:
            async with semaphore:
                self.inventory.record_event(event)
                markets = await discover(
                    "markets",
                    event.source_event_id,
                    lambda: provider.get_event_markets(event, package),
                )
                if markets is None:
                    return
                try:
                    snapshot = self.inventory.record_markets(event, markets)
                except Exception as exc:
                    report.failures.append(
                        ScanFailure("inventory", event.source_event_id, f"{type(exc).__name__}: {exc}")
                    )
                    return
                report.events_scanned += 1
                report.market_snapshots_recorded += 1
                report.markets_received += len(snapshot.markets)
                report.selections_received += sum(
                    len(market.selections) for market in snapshot.markets
                )

        await asyncio.gather(*(scan_event(event) for event in events_by_key.values()))
        report.completed_at = datetime.now(timezone.utc)
        return report
