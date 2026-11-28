from datetime import datetime, timezone, timedelta

from app.providers.base import ProviderEvent, ProviderMarket, ProviderSelection
from app.services.market_inventory import EventMarketSnapshot
from app.services.market_movement import summarize_odds_movement
from app.services.sqlite_store import SQLiteMarketStore


def record_price_snapshot(store, scan_id, captured_at, odds):
    event = ProviderEvent(
        provider="book-a",
        source_event_id="event-1",
        sport="football",
        competition="league-1",
        name="Home v Away",
        start_time=None,
        status="scheduled",
    )
    store.start_scan(
        scan_id, "book-a", "2026-11-28", "standard", captured_at.isoformat()
    )
    store.record_event(event, captured_at.isoformat())
    market = ProviderMarket(
        provider="book-a",
        source_event_id="event-1",
        source_market_id="market-1",
        name="Match Winner",
        period="full_time",
        line=None,
        status="active",
        selections=[ProviderSelection("home", "Home", odds)],
        classified=True,
    )
    snapshot = EventMarketSnapshot(
        provider="book-a",
        source_event_id="event-1",
        captured_at=captured_at,
        markets=(market,),
    )
    store.record_snapshot(snapshot, scan_id)


def test_selection_price_history_is_chronological_and_scoped_to_source_ids(tmp_path):
    store = SQLiteMarketStore(tmp_path / "movement.sqlite3")
    base = datetime(2026, 11, 28, 10, 0, tzinfo=timezone.utc)

    record_price_snapshot(store, "scan-1", base + timedelta(minutes=10), 1.80)
    record_price_snapshot(store, "scan-2", base, 2.00)

    history = store.selection_price_history(
        "book-a", "event-1", "market-1", "home"
    )

    assert [item["odds_decimal"] for item in history] == [2.0, 1.8]
    assert history[0]["selection_name"] == "Home"


def test_odds_movement_identifies_shortening_and_drift():
    shortening = summarize_odds_movement([
        {"captured_at": "t1", "odds_decimal": 2.0},
        {"captured_at": "t2", "odds_decimal": 1.8},
    ])
    assert shortening["direction"] == "shortened"
    assert shortening["percentage_change"] == -10.0

    drifting = summarize_odds_movement([
        {"captured_at": "t1", "odds_decimal": 1.8},
        {"captured_at": "t2", "odds_decimal": 2.0},
    ])
    assert drifting["direction"] == "drifted"
    assert drifting["percentage_change"] == 11.1111


def test_odds_movement_does_not_claim_movement_from_one_observation():
    result = summarize_odds_movement([
        {"captured_at": "t1", "odds_decimal": 1.9}
    ])
    assert result["status"] == "insufficient_observations"
    assert result["direction"] is None
    assert result["percentage_change"] is None


def test_odds_movement_handles_empty_history():
    result = summarize_odds_movement([])
    assert result["status"] == "no_observations"
    assert result["observation_count"] == 0
