import asyncio
import json

from app.providers.base import ProviderEvent, ProviderMarket, ProviderSelection
from app.providers.registry import ProviderRegistry
from app.services.ingestion import IngestionOrchestrator
from app.services.market_inventory import MarketInventory
from app.services.sqlite_store import SQLiteMarketStore


class PersistentMockProvider:
    provider_id = "persistent-mock"

    async def list_books(self):
        return [{"id": "book-1"}]

    async def list_sports(self):
        return [{"id": "football"}]

    async def list_competitions(self, sport_id):
        return [{"id": "league-1"}]

    async def list_events(self, competition_id, date):
        return [
            ProviderEvent(
                provider=self.provider_id,
                source_event_id="event-1",
                sport="football",
                competition=competition_id,
                name="Home v Away",
                start_time=None,
                status="scheduled",
                raw={"source": "fixture-feed"},
            )
        ]

    async def get_event_markets(self, event, package):
        return [
            ProviderMarket(
                provider=self.provider_id,
                source_event_id=event.source_event_id,
                source_market_id="unmapped-1",
                name="New provider market",
                period=None,
                line=None,
                status="active",
                selections=[
                    ProviderSelection(
                        "yes", "Yes", 1.85, raw={"source_outcome_code": "Y"}
                    )
                ],
                raw={"source_market_code": "CUSTOM_99"},
                classified=False,
            )
        ]


def test_store_persists_scan_events_and_unclassified_market_snapshots(tmp_path):
    database = tmp_path / "history.sqlite3"
    store = SQLiteMarketStore(database)
    provider = PersistentMockProvider()
    orchestrator = IngestionOrchestrator(
        ProviderRegistry([provider]),
        MarketInventory(),
        store=store,
        max_retries=0,
    )

    report = asyncio.run(orchestrator.scan("persistent-mock", "2026-11-28"))

    assert report.complete
    assert report.market_snapshots_recorded == 1

    # Re-open the database to prove the data is not just held in process memory.
    reopened = SQLiteMarketStore(database)
    coverage = reopened.coverage_report()
    assert coverage["snapshot_count"] == 1
    stats = coverage["providers"]["persistent-mock"]
    assert stats["events_scanned"] == 1
    assert stats["markets_received"] == 1
    assert stats["selections_received"] == 1
    assert stats["unclassified_markets"] == 1

    history = reopened.scan_history()
    assert len(history) == 1
    assert history[0]["status"] == "complete"
    assert history[0]["report"]["markets_received"] == 1

    snapshots = reopened.snapshots_for_event("persistent-mock", "event-1")
    assert len(snapshots) == 1
    market = snapshots[0]["markets"][0]
    assert market["raw"]["source_market_code"] == "CUSTOM_99"
    assert market["selections"][0]["raw"]["source_outcome_code"] == "Y"
    assert market["classified"] is False


def test_store_records_partial_scan_failures(tmp_path):
    database = tmp_path / "partial.sqlite3"
    store = SQLiteMarketStore(database)

    class PartiallyFailingProvider(PersistentMockProvider):
        async def get_event_markets(self, event, package):
            raise TimeoutError("market endpoint timed out")

    orchestrator = IngestionOrchestrator(
        ProviderRegistry([PartiallyFailingProvider()]),
        MarketInventory(),
        store=store,
        max_retries=0,
    )
    report = asyncio.run(orchestrator.scan("persistent-mock", "2026-11-28"))

    assert not report.complete
    history = store.scan_history()
    assert history[0]["status"] == "partial"
    assert history[0]["report"]["failures"][0]["stage"] == "markets"


def test_bookmaker_specific_price_history_requires_book_filter_when_ambiguous(tmp_path):
    from datetime import datetime, timezone
    import pytest
    from app.providers.base import ProviderEvent, ProviderMarket, ProviderSelection
    from app.services.market_inventory import EventMarketSnapshot

    store = SQLiteMarketStore(tmp_path / "book-filter.sqlite3")
    event = ProviderEvent(
        provider="sportradar-prematch",
        source_event_id="event-1",
        sport="football",
        competition="league",
        name="Home v Away",
        start_time=None,
        status="scheduled",
    )
    for book_id, price in (("book-a", 1.8), ("book-b", 1.9)):
        scan_id = f"scan-{book_id}"
        store.start_scan(scan_id, "sportradar-prematch", "2026-11-28", "prematch",
                         "2026-11-28T10:00:00+00:00")
        store.record_event(event, "2026-11-28T10:00:00+00:00")
        market = ProviderMarket(
            provider="sportradar-prematch",
            source_event_id="event-1",
            source_market_id="market-1",
            name="Match Winner",
            period=None,
            line=None,
            status="active",
            selections=[ProviderSelection("home", "Home", price)],
            source_book_id=book_id,
            source_book_name=book_id,
        )
        snapshot = EventMarketSnapshot(
            provider="sportradar-prematch",
            source_event_id="event-1",
            captured_at=datetime(2026, 11, 28, 10, 0, tzinfo=timezone.utc),
            markets=(market,),
        )
        store.record_snapshot(snapshot, scan_id)

    with pytest.raises(ValueError, match="source_book_id is required"):
        store.selection_price_history("sportradar-prematch", "event-1", "market-1", "home")

    filtered = store.selection_price_history(
        "sportradar-prematch", "event-1", "market-1", "home",
        source_book_id="book-b",
    )
    assert len(filtered) == 1
    assert filtered[0]["source_book_id"] == "book-b"
    assert filtered[0]["odds_decimal"] == 1.9


def test_discovery_inventory_persists_exact_provider_catalogue_payloads(tmp_path):
    store = SQLiteMarketStore(tmp_path / "discovery.sqlite3")
    store.start_scan(
        "scan-discovery", "sportradar-prematch", "2026-11-28", "prematch",
        "2026-11-28T10:00:00+00:00",
    )
    store.record_discovery_items(
        "scan-discovery", "sportradar-prematch", "books", "sportradar-prematch",
        "prematch",
        [{"id": "sr:book:7", "name": "Book Seven", "country": "NG"}],
        "2026-11-28T10:00:01+00:00",
    )
    store.record_discovery_items(
        "scan-discovery", "sportradar-prematch", "competitions", "sr:sport:1",
        "prematch",
        [{"id": "sr:competition:17", "name": "Premier League", "markets": True}],
        "2026-11-28T10:00:02+00:00",
    )
    reopened = SQLiteMarketStore(tmp_path / "discovery.sqlite3")
    books = reopened.discovery_inventory(provider="sportradar-prematch", stage="books")
    competitions = reopened.discovery_inventory(stage="competitions")
    assert books[0]["source_id"] == "sr:book:7"
    assert books[0]["raw"]["country"] == "NG"
    assert competitions[0]["raw"]["markets"] is True
    assert books[0]["scan_id"] == "scan-discovery"


def test_discovery_inventory_validates_stage_and_limit(tmp_path):
    import pytest
    store = SQLiteMarketStore(tmp_path / "discovery-validation.sqlite3")
    with pytest.raises(ValueError, match="stage must"):
        store.discovery_inventory(stage="events")
    with pytest.raises(ValueError, match="limit"):
        store.discovery_inventory(limit=0)


def test_source_book_coverage_reports_observed_provider_book_inventory(tmp_path):
    from datetime import datetime, timezone
    from app.providers.base import ProviderEvent, ProviderMarket, ProviderSelection
    from app.services.market_inventory import EventMarketSnapshot

    store = SQLiteMarketStore(tmp_path / "book-coverage.sqlite3")
    event = ProviderEvent(
        provider="feed-a", source_event_id="event-a", sport="basketball",
        competition="league-a", name="Home v Away", start_time=None, status="scheduled",
    )
    store.start_scan("scan-a", "feed-a", "2026-11-28", "prematch",
                     "2026-11-28T10:00:00+00:00")
    store.record_event(event, "2026-11-28T10:00:00+00:00")
    markets = (
        ProviderMarket(
            provider="feed-a", source_event_id="event-a",
            source_market_id="market-1", name="Moneyline", period="full_game",
            line=None, status="active",
            selections=[ProviderSelection("home", "Home", 1.8)],
            source_book_id="book-xyz", source_book_name="Example Book",
        ),
        ProviderMarket(
            provider="feed-a", source_event_id="event-a",
            source_market_id="market-2", name="Total Points", period="full_game",
            line=210.5, status="active",
            selections=[
                ProviderSelection("over", "Over", 1.9),
                ProviderSelection("under", "Under", 1.9),
            ],
            source_book_id="book-xyz", source_book_name="Example Book",
        ),
        ProviderMarket(
            provider="feed-a", source_event_id="event-a",
            source_market_id="market-3", name="Unattributed market",
            period="full_game", line=None, status="active",
            selections=[ProviderSelection("yes", "Yes", 2.0)],
        ),
    )
    store.record_snapshot(
        EventMarketSnapshot(
            provider="feed-a", source_event_id="event-a",
            captured_at=datetime(2026, 11, 28, 10, 0, tzinfo=timezone.utc),
            markets=markets,
        ),
        "scan-a",
    )

    report = store.source_book_coverage_report()
    assert report["source_book_count"] == 1
    assert report["unattributed_market_observations"] == 1
    observed = report["source_books"][0]
    assert observed["provider_id"] == "feed-a"
    assert observed["source_book_id"] == "book-xyz"
    assert observed["source_book_name"] == "Example Book"
    assert observed["events_observed"] == 1
    assert observed["market_observations"] == 2
    assert observed["selections_received"] == 3
    assert observed["packages_observed"] == ["prematch"]
    assert observed["sports_observed"] == ["basketball"]
    assert observed["competitions_observed"] == ["league-a"]
    filtered = store.source_book_coverage_report(provider="feed-a")
    assert filtered["source_book_count"] == 1


def test_source_book_coverage_can_be_filtered_by_provider(tmp_path):
    store = SQLiteMarketStore(tmp_path / "provider-coverage.sqlite3")
    assert store.source_book_coverage_report(provider="missing-feed")["source_book_count"] == 0
