from datetime import datetime, timezone

import pytest

from app.providers.base import ProviderEvent, ProviderMarket, ProviderSelection
from app.services.market_inventory import MarketInventory


def make_event():
    return ProviderEvent(
        provider="demo-book",
        source_event_id="event-123",
        sport="football",
        competition="test-league",
        name="Home FC v Away FC",
        start_time=None,
        status="scheduled",
    )


def make_market(classified=True):
    return ProviderMarket(
        provider="demo-book",
        source_event_id="event-123",
        source_market_id="market-1",
        name="Match Winner",
        period="full_time",
        line=None,
        status="active",
        selections=[
            ProviderSelection("home", "Home FC", 2.1),
            ProviderSelection("draw", "Draw", 3.2),
            ProviderSelection("away", "Away FC", 3.5),
        ],
        classified=classified,
    )


def test_inventory_preserves_markets_and_unknown_market_types():
    inventory = MarketInventory()
    event = make_event()
    inventory.record_event(event)
    unknown = make_market(classified=False)

    snapshot = inventory.record_markets(
        event, [make_market(), unknown],
        captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert len(snapshot.markets) == 2
    assert snapshot.markets[1] is unknown
    assert snapshot.markets[1].classified is False
    assert len(snapshot.markets[1].selections) == 3


def test_coverage_report_counts_events_markets_selections_and_unknowns():
    inventory = MarketInventory()
    event = make_event()
    inventory.record_event(event)
    inventory.record_markets(event, [make_market(), make_market(False)])

    report = inventory.coverage_report()
    stats = report["providers"]["demo-book"]
    assert stats["events_scanned"] == 1
    assert stats["snapshots"] == 1
    assert stats["markets_received"] == 2
    assert stats["selections_received"] == 6
    assert stats["unclassified_markets"] == 1


def test_inventory_requires_event_before_markets():
    inventory = MarketInventory()
    with pytest.raises(KeyError):
        inventory.record_markets(make_event(), [make_market()])


def test_inventory_rejects_market_from_another_event():
    inventory = MarketInventory()
    event = make_event()
    inventory.record_event(event)
    market = make_market()
    market = ProviderMarket(
        provider=market.provider,
        source_event_id="different-event",
        source_market_id=market.source_market_id,
        name=market.name,
        period=market.period,
        line=market.line,
        status=market.status,
        selections=market.selections,
    )
    with pytest.raises(ValueError):
        inventory.record_markets(event, [market])
