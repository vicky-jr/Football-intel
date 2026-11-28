from datetime import datetime, timedelta, timezone

import pytest

from app.services.data_quality import assess_market_freshness


NOW = datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc)


def iso(minutes_ago=0):
    return (NOW - timedelta(minutes=minutes_ago)).isoformat()


def test_source_freshness_and_collection_recency_are_reported_separately():
    result = assess_market_freshness(
        {"source_updated_at": iso(1)},
        captured_at=iso(0),
        max_age_seconds=300,
        now=NOW,
    )
    assert result["source_freshness"] == "fresh"
    assert result["collection_recency"] == "fresh"
    assert result["safe_to_treat_as_source_fresh"] is True


def test_recent_collection_does_not_hide_stale_provider_source_timestamp():
    result = assess_market_freshness(
        {"source_updated_at": iso(20)},
        captured_at=iso(0),
        max_age_seconds=300,
        now=NOW,
    )
    assert result["collection_recency"] == "fresh"
    assert result["source_freshness"] == "stale"
    assert result["safe_to_treat_as_source_fresh"] is False


def test_missing_provider_timestamp_stays_unknown_even_if_just_collected():
    result = assess_market_freshness(
        {},
        captured_at=iso(0),
        max_age_seconds=300,
        now=NOW,
    )
    assert result["collection_recency"] == "fresh"
    assert result["source_freshness"] == "unknown"
    assert result["source_timestamp_quality"] == "missing"
    assert result["safe_to_treat_as_source_fresh"] is False


def test_naive_provider_timestamp_is_not_assumed_to_be_utc():
    result = assess_market_freshness(
        {"source_updated_at": "2026-11-28T11:59:00"},
        captured_at=iso(0),
        max_age_seconds=300,
        now=NOW,
    )
    assert result["source_freshness"] == "unknown"
    assert result["source_timestamp_quality"] == "invalid_or_timezone_missing"


def test_future_timestamp_is_flagged():
    future = (NOW + timedelta(minutes=5)).isoformat()
    result = assess_market_freshness(
        {"source_updated_at": future},
        captured_at=iso(0),
        now=NOW,
    )
    assert result["source_freshness"] == "future_timestamp"


def test_invalid_threshold_and_naive_assessment_time_are_rejected():
    with pytest.raises(ValueError):
        assess_market_freshness({}, iso(), max_age_seconds=-1, now=NOW)
    with pytest.raises(ValueError):
        assess_market_freshness({}, iso(), now=datetime(2026, 11, 28, 12, 0))
