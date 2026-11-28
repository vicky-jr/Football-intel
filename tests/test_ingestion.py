import asyncio

from app.providers.base import ProviderEvent, ProviderMarket, ProviderSelection
from app.providers.registry import ProviderRegistry
from app.services.ingestion import IngestionOrchestrator
from app.services.market_inventory import MarketInventory


class MockProvider:
    provider_id = "mock"

    def __init__(self, *, fail_event=None, transient_once=False):
        self.fail_event = fail_event
        self.transient_once = transient_once
        self.market_calls = {}

    async def list_books(self):
        return [{"id": "book-1", "name": "Mock Book"}]

    async def list_sports(self):
        return [{"id": "football", "name": "Football"}]

    async def list_competitions(self, sport_id):
        assert sport_id == "football"
        return [{"id": "league-1", "name": "Test League"}]

    async def list_events(self, competition_id, date):
        assert competition_id == "league-1"
        assert date == "2026-11-28"
        return [
            ProviderEvent("mock", "event-1", "football", "league-1", "A v B", None, "scheduled"),
            # Duplicate delivery should be scanned once per provider/event in this run.
            ProviderEvent("mock", "event-1", "football", "league-1", "A v B", None, "scheduled"),
            ProviderEvent("mock", "event-2", "football", "league-1", "C v D", None, "scheduled"),
        ]

    async def get_event_markets(self, event, package):
        assert package == "standard"
        calls = self.market_calls.get(event.source_event_id, 0) + 1
        self.market_calls[event.source_event_id] = calls
        if event.source_event_id == self.fail_event:
            raise RuntimeError("provider temporarily unavailable")
        if self.transient_once and event.source_event_id == "event-1" and calls == 1:
            raise TimeoutError("temporary timeout")
        return [
            ProviderMarket(
                provider="mock",
                source_event_id=event.source_event_id,
                source_market_id="market-1",
                name="Unmapped source market",
                period=None,
                line=None,
                status="active",
                selections=[ProviderSelection("selection-1", "Yes", 1.9)],
                classified=False,
            )
        ]


def make_orchestrator(provider, *, retries=1):
    registry = ProviderRegistry([provider])
    inventory = MarketInventory()
    orchestrator = IngestionOrchestrator(
        registry, inventory, max_concurrency=2, max_retries=retries
    )
    return orchestrator, inventory


def test_scan_discovers_and_preserves_all_returned_markets():
    provider = MockProvider(transient_once=True)
    orchestrator, inventory = make_orchestrator(provider)

    report = asyncio.run(
        orchestrator.scan("mock", "2026-11-28", package="standard")
    )

    assert report.complete
    assert report.books_discovered == 1
    assert report.sports_discovered == 1
    assert report.competitions_discovered == 1
    assert report.events_discovered == 2
    assert report.events_scanned == 2
    assert report.market_snapshots_recorded == 2
    assert report.markets_received == 2
    assert report.selections_received == 2
    assert provider.market_calls["event-1"] == 2
    assert len(inventory.snapshots_for_event("mock", "event-1")) == 1
    assert inventory.snapshots_for_event("mock", "event-1")[0].markets[0].classified is False


def test_scan_isolates_event_market_failure_and_reports_partial_completion():
    provider = MockProvider(fail_event="event-2")
    orchestrator, inventory = make_orchestrator(provider, retries=0)

    report = asyncio.run(orchestrator.scan("mock", "2026-11-28", package="standard"))

    assert not report.complete
    assert report.events_discovered == 2
    assert report.events_scanned == 1
    assert report.markets_received == 1
    assert len(report.failures) == 1
    assert report.failures[0].stage == "markets"
    assert report.failures[0].scope == "event-2"
    assert len(inventory.snapshots_for_event("mock", "event-1")) == 1
    assert inventory.snapshots_for_event("mock", "event-2") == []


def test_scan_rejects_invalid_concurrency_and_retry_configuration():
    provider = MockProvider()
    registry = ProviderRegistry([provider])
    inventory = MarketInventory()

    try:
        IngestionOrchestrator(registry, inventory, max_concurrency=0)
    except ValueError as exc:
        assert "max_concurrency" in str(exc)
    else:
        raise AssertionError("expected invalid concurrency to be rejected")

    try:
        IngestionOrchestrator(registry, inventory, max_retries=-1)
    except ValueError as exc:
        assert "max_retries" in str(exc)
    else:
        raise AssertionError("expected negative retries to be rejected")


def test_stage_based_sports_are_reported_as_coverage_warnings():
    class StageSportProvider(MockProvider):
        async def list_sports(self):
            return [
                {"id": "golf", "name": "Golf", "type": "stage"},
                {"id": "football", "name": "Football", "type": "competition"},
            ]

        async def list_competitions(self, sport_id):
            assert sport_id == "football"
            return [{"id": "league-1", "name": "Test League"}]

    provider = StageSportProvider()
    orchestrator, inventory = make_orchestrator(provider)
    report = asyncio.run(
        orchestrator.scan("mock", "2026-11-28", package="standard")
    )

    assert report.events_scanned == 2
    assert report.coverage_warnings
    assert "Stage-based sport Golf" in report.coverage_warnings[0]
    assert not report.complete
    # The stage sport was not incorrectly sent to the competition endpoint.
    assert len(inventory.snapshots_for_event("mock", "event-1")) == 1
