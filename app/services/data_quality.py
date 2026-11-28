"""Data freshness and timestamp-quality assessment for captured markets."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _parse_aware_timestamp(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _age_status(
    timestamp: datetime | None,
    now: datetime,
    max_age_seconds: int,
    future_tolerance_seconds: int,
) -> tuple[str, float | None]:
    if timestamp is None:
        return "unknown", None
    age = (now - timestamp).total_seconds()
    if age < -future_tolerance_seconds:
        return "future_timestamp", round(age, 3)
    if age > max_age_seconds:
        return "stale", round(age, 3)
    return "fresh", round(age, 3)


def assess_market_freshness(
    market: dict[str, Any],
    captured_at: str,
    *,
    max_age_seconds: int = 300,
    now: datetime | None = None,
    future_tolerance_seconds: int = 60,
) -> dict[str, Any]:
    """Separate provider-source freshness from our own collection recency.

    A missing provider timestamp is never promoted to source-fresh merely
    because our collector just downloaded the response.
    """
    if max_age_seconds < 0:
        raise ValueError("max_age_seconds cannot be negative")
    if future_tolerance_seconds < 0:
        raise ValueError("future_tolerance_seconds cannot be negative")

    assessed_at = now or datetime.now(timezone.utc)
    if assessed_at.tzinfo is None or assessed_at.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    assessed_at = assessed_at.astimezone(timezone.utc)

    captured = _parse_aware_timestamp(captured_at)
    collection_status, collection_age = _age_status(
        captured, assessed_at, max_age_seconds, future_tolerance_seconds
    )

    source_raw = market.get("source_updated_at")
    source_timestamp = _parse_aware_timestamp(source_raw)
    source_status, source_age = _age_status(
        source_timestamp, assessed_at, max_age_seconds, future_tolerance_seconds
    )
    if not source_raw:
        source_timestamp_quality = "missing"
    elif source_timestamp is None:
        source_timestamp_quality = "invalid_or_timezone_missing"
    else:
        source_timestamp_quality = "valid"

    return {
        "assessed_at": assessed_at.isoformat(),
        "max_age_seconds": max_age_seconds,
        "collection_recency": collection_status,
        "collection_age_seconds": collection_age,
        "captured_at": captured_at,
        "source_freshness": source_status,
        "source_age_seconds": source_age,
        "source_updated_at": source_raw,
        "source_timestamp_quality": source_timestamp_quality,
        "safe_to_treat_as_source_fresh": source_status == "fresh",
    }
