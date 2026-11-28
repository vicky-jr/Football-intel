"""Descriptive odds-movement calculations over observed provider snapshots."""
from __future__ import annotations

from typing import Any


def summarize_odds_movement(observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Describe price changes without inferring outcomes or fair probabilities.

    The first observation means the first price captured by this system, not
    necessarily the bookmaker's true opening price.
    """
    if not observations:
        return {
            "status": "no_observations",
            "observation_count": 0,
            "first_observed_price": None,
            "latest_price": None,
            "absolute_change": None,
            "percentage_change": None,
            "direction": None,
        }

    first = observations[0]
    latest = observations[-1]
    opening_price = float(first["odds_decimal"])
    latest_price = float(latest["odds_decimal"])

    if len(observations) < 2:
        return {
            "status": "insufficient_observations",
            "observation_count": 1,
            "first_observed_price": opening_price,
            "latest_price": latest_price,
            "absolute_change": None,
            "percentage_change": None,
            "direction": None,
        }

    absolute_change = latest_price - opening_price
    percentage_change = (absolute_change / opening_price) * 100
    if latest_price < opening_price:
        direction = "shortened"
    elif latest_price > opening_price:
        direction = "drifted"
    else:
        direction = "unchanged"

    return {
        "status": "observed",
        "observation_count": len(observations),
        "first_observed_at": first.get("captured_at"),
        "latest_observed_at": latest.get("captured_at"),
        "first_observed_price": opening_price,
        "latest_price": latest_price,
        "absolute_change": round(absolute_change, 6),
        "percentage_change": round(percentage_change, 4),
        "direction": direction,
    }
