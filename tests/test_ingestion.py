import asyncio

import httpx
import pytest

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


def _http_status_error(status_code, headers=None):
    request = httpx.Request("GET", "https://provider.example/feed")
    response = httpx.Response(status_code, headers=headers, request=request)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return exc
    raise AssertionError(f"HTTP {status_code} should be an error")


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


def test_stage_based_sports_without_stage_adapter_are_reported_as_coverage_warnings():
    class StageSportProvider(MockProvider):
        async def list_sports(self):
            return [{"id": "golf", "name": "Golf", "type": "stage"}]

    provider = StageSportProvider()
    orchestrator, inventory = make_orchestrator(provider)
    report = asyncio.run(
        orchestrator.scan("mock", "2026-11-28", package="standard")
    )

    assert report.events_scanned == 0
    assert any("Stage-based sport Golf is not supported" in item for item in report.coverage_warnings)
    assert not report.complete
    assert inventory.snapshots_for_event("mock", "event-1") == []


def test_stage_based_sports_use_stage_catalogue_and_daily_events():
    class StageSportProvider(MockProvider):
        async def list_sports(self):
            return [{"id": "golf", "name": "Golf", "type": "stage"}]

        async def list_stages(self, sport_id):
            assert sport_id == "golf"
            return [
                {"id": "stage-1", "description": "The Open"},
                {"id": "stage-2", "description": "Another Tournament"},
            ]

        async def list_sport_events(self, sport_id, date):
            assert sport_id == "golf"
            assert date == "2026-11-28"
            return [
                ProviderEvent("mock", "golf-event-1", "Golf", "The Open",
                              "The Open - Round 1", "2026-11-28T08:00:00+00:00",
                              "scheduled", raw={"stage_id": "stage-1"}),
                ProviderEvent("mock", "golf-event-2", "Golf", "Another Tournament",
                              "Another Tournament - Round 1", "2026-11-28T09:00:00+00:00",
                              "scheduled", raw={"stage_id": "stage-2"}),
            ]

        async def list_competitions(self, sport_id):
            raise AssertionError("stage sports must not use the competitions feed")

    provider = StageSportProvider()
    orchestrator, inventory = make_orchestrator(provider)
    report = asyncio.run(
        orchestrator.scan(
            "mock", "2026-11-28", package="standard",
            competition_ids={"stage-1"},
        )
    )

    assert report.complete
    assert report.stages_discovered == 2
    assert report.competitions_discovered == 0
    assert report.events_discovered == 1
    assert report.events_scanned == 1
    assert inventory.snapshots_for_event("mock", "golf-event-1")
    assert inventory.snapshots_for_event("mock", "golf-event-2") == []


def test_scan_can_be_scoped_to_sport_and_competition():
    class MultiCompetitionProvider(MockProvider):
        def __init__(self):
            super().__init__()
            self.competition_calls = []

        async def list_competitions(self, sport_id):
            self.competition_calls.append(sport_id)
            return [
                {"id": "league-1", "name": "Test League", "markets": True},
                {"id": "league-2", "name": "Other League", "markets": True},
            ]

        async def list_events(self, competition_id, date):
            if competition_id == "league-2":
                return []
            return await super().list_events(competition_id, date)

    provider = MultiCompetitionProvider()
    orchestrator, inventory = make_orchestrator(provider)
    report = asyncio.run(
        orchestrator.scan(
            "mock", "2026-11-28", package="standard",
            sport_ids={"football"}, competition_ids={"league-1"},
        )
    )
    assert report.complete
    assert provider.competition_calls == ["football"]
    assert report.competitions_discovered == 1
    assert report.events_scanned == 2


def test_scan_reports_unknown_requested_sport_as_coverage_warning():
    provider = MockProvider()
    orchestrator, _ = make_orchestrator(provider)
    report = asyncio.run(
        orchestrator.scan(
            "mock", "2026-11-28", package="standard", sport_ids={"unknown-sport"}
        )
    )
    assert not report.complete
    assert report.events_discovered == 0
    assert any("not present in this provider catalogue" in item for item in report.coverage_warnings)


@pytest.mark.parametrize("status_code", [408, 425, 429, 500, 502, 503, 599])
def test_retry_retries_transient_http_statuses(status_code):
    orchestrator, _ = make_orchestrator(MockProvider(), retries=1)
    calls = 0

    async def operation():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise _http_status_error(status_code, {"retry-after": "0"})
        return "recovered"

    assert asyncio.run(orchestrator._retry(operation)) == "recovered"
    assert calls == 2


@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 422])
def test_retry_does_not_repeat_permanent_http_statuses(status_code):
    orchestrator, _ = make_orchestrator(MockProvider(), retries=3)
    calls = 0

    async def operation():
        nonlocal calls
        calls += 1
        raise _http_status_error(status_code)

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(orchestrator._retry(operation))
    assert calls == 1


def test_retry_preserves_retry_after_http_date_support():
    error = _http_status_error(429, {"Retry-After": "Wed, 21 Oct 2030 07:28:00 GMT"})
    assert IngestionOrchestrator._retry_after_seconds(error) > 0


def test_retry_does_not_repeat_unclassified_programming_errors():
    orchestrator, _ = make_orchestrator(MockProvider(), retries=3)
    calls = 0

    async def operation():
        nonlocal calls
        calls += 1
        raise ValueError("invalid provider response")

    with pytest.raises(ValueError, match="invalid provider response"):
        asyncio.run(orchestrator._retry(operation))
    assert calls == 1
