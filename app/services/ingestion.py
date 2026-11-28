"""Provider-neutral orchestration for bounded market-discovery scans.

The orchestrator preserves every returned market and can optionally persist
scan history, events and timestamped market snapshots through a storage adapter.
Provider adapters are responsible for exhausting permitted pagination and
reporting only data their account may access.
"""
from __future__ import annotations

import asyncio
import uuid
from email.utils import parsedate_to_datetime
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, TypeVar

from app.providers.base import OddsProvider, ProviderEvent
from app.providers.registry import ProviderRegistry
from app.services.market_inventory import MarketInventory
from app.services.sqlite_store import SQLiteMarketStore

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
    coverage_warnings: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return self.completed_at is not None and not self.failures and not self.coverage_warnings


class IngestionOrchestrator:
    """Run a bounded, failure-isolated discovery scan for one registered provider."""

    def __init__(
        self,
        registry: ProviderRegistry,
        inventory: MarketInventory,
        *,
        store: SQLiteMarketStore | None = None,
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
        self.store = store
        self.max_concurrency = max_concurrency
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

    async def _retry(self, operation: Callable[[], Awaitable[T]]) -> T:
        for attempt in range(self.max_retries + 1):
            try:
                return await operation()
            except Exception as exc:
                if attempt >= self.max_retries:
                    raise
                retry_after = None
                response = getattr(exc, "response", None)
                headers = getattr(response, "headers", {}) if response is not None else {}
                raw_retry_after = headers.get("retry-after") if headers else None
                if raw_retry_after:
                    try:
                        retry_after = max(0.0, float(raw_retry_after))
                    except (TypeError, ValueError):
                        try:
                            retry_time = parsedate_to_datetime(raw_retry_after)
                            if retry_time.tzinfo is None:
                                retry_time = retry_time.replace(tzinfo=timezone.utc)
                            retry_after = max(
                                0.0,
                                (retry_time - datetime.now(timezone.utc)).total_seconds(),
                            )
                        except (TypeError, ValueError, OverflowError):
                            retry_after = None
                delay = retry_after if retry_after is not None else self.retry_delay_seconds * (2 ** attempt)
                if delay:
                    await asyncio.sleep(delay)
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
        sport_ids: set[str] | None = None,
        competition_ids: set[str] | None = None,
    ) -> IngestionReport:
        provider: OddsProvider = self.registry.get(provider_id)
        selected_sports = {str(value).strip() for value in sport_ids or set()}
        selected_competitions = {str(value).strip() for value in competition_ids or set()}
        if any(not value for value in selected_sports | selected_competitions):
            raise ValueError("sport and competition filters cannot contain blank IDs")
        started = datetime.now(timezone.utc)
        scan_id = str(uuid.uuid4())
        report = IngestionReport(
            provider=provider.provider_id,
            scan_date=scan_date,
            started_at=started,
        )
        if self.store is not None:
            self.store.start_scan(
                scan_id, provider.provider_id, scan_date, package, started.isoformat()
            )

        def finish() -> None:
            report.completed_at = datetime.now(timezone.utc)
            if self.store is not None:
                self.store.finish_scan(scan_id, report)

        async def discover(stage: str, scope: str, operation: Callable[[], Awaitable[T]]) -> T | None:
            try:
                return await self._retry(operation)
            except Exception as exc:
                report.failures.append(ScanFailure(stage, scope, f"{type(exc).__name__}: {exc}"))
                return None

        books = await discover("books", provider.provider_id, provider.list_books)
        if books is not None:
            report.books_discovered = len(books)
            if self.store is not None:
                self.store.record_discovery_items(
                    scan_id, provider.provider_id, "books", provider.provider_id,
                    package, books, datetime.now(timezone.utc).isoformat(),
                )

        sports = await discover("sports", provider.provider_id, provider.list_sports)
        if sports is not None:
            report.sports_discovered = len(sports)
            if self.store is not None:
                self.store.record_discovery_items(
                    scan_id, provider.provider_id, "sports", provider.provider_id,
                    package, sports, datetime.now(timezone.utc).isoformat(),
                )

        if sports is None:
            finish()
            return report

        competitions: list[tuple[str, str]] = []
        discovered_competition_ids: set[str] = set()
        for sport in sports:
            try:
                sport_id = self._source_id(sport, scope="sport")
            except ValueError as exc:
                report.failures.append(ScanFailure("competitions", "unknown-sport", str(exc)))
                continue

            if selected_sports and sport_id not in selected_sports:
                continue

            sport_type = str(sport.get("type") or "competition").casefold()
            if sport_type == "stage":
                report.coverage_warnings.append(
                    f"Stage-based sport {sport.get('name') or sport_id} is not yet supported by the Prematch event-schedule adapter."
                )
                continue
            if sport_type != "competition":
                report.coverage_warnings.append(
                    f"Unknown sport catalogue type '{sport_type}' for {sport.get('name') or sport_id}; skipped safely."
                )
                continue

            items = await discover(
                "competitions",
                sport_id,
                lambda sport_id=sport_id: provider.list_competitions(sport_id),
            )
            if items is None:
                continue
            if self.store is not None:
                self.store.record_discovery_items(
                    scan_id, provider.provider_id, "competitions", sport_id,
                    package, items, datetime.now(timezone.utc).isoformat(),
                )

            for item in items:
                try:
                    competition_id = self._source_id(item, scope="competition")
                except ValueError as exc:
                    report.failures.append(ScanFailure("events", sport_id, str(exc)))
                    continue
                discovered_competition_ids.add(competition_id)
                if selected_competitions and competition_id not in selected_competitions:
                    continue
                if item.get("markets") is False:
                    continue
                competitions.append((sport_id, competition_id))

        if selected_sports:
            discovered_sport_ids = {
                str(item.get("id") or item.get("source_id"))
                for item in sports if item.get("id") or item.get("source_id")
            }
            for missing in sorted(selected_sports - discovered_sport_ids):
                report.coverage_warnings.append(
                    f"Requested sport ID was not present in this provider catalogue: {missing}"
                )

        if selected_competitions:
            for missing in sorted(selected_competitions - discovered_competition_ids):
                report.coverage_warnings.append(
                    f"Requested competition ID was not present in this provider catalogue: {missing}"
                )

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
                if self.store is not None:
                    self.store.record_event(event, datetime.now(timezone.utc).isoformat())
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
                if self.store is not None:
                    try:
                        self.store.record_snapshot(snapshot, scan_id)
                    except Exception as exc:
                        report.failures.append(
                            ScanFailure("persistence", event.source_event_id, f"{type(exc).__name__}: {exc}")
                        )
                        return
                report.events_scanned += 1
                report.market_snapshots_recorded += 1
                report.markets_received += len(snapshot.markets)
                report.selections_received += sum(
                    len(market.selections) for market in snapshot.markets
                )

        await asyncio.gather(*(scan_event(event) for event in events_by_key.values()))
        finish()
        return report
