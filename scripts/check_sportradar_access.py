"""Check Sportradar Prematch credentials and catalogue access without collecting event odds.

This utility prints only access metadata and counts. It never logs the API key
or the detailed licensed bookmaker catalogue.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.providers.sportradar import SportradarPrematchProvider, provider_from_environment


async def inspect_access(provider: SportradarPrematchProvider | None = None) -> dict[str, Any]:
    active_provider = provider or provider_from_environment()
    try:
        books = await active_provider.list_books()
        sports = await active_provider.list_sports()
        competition_sports = sum(
            str(item.get("type") or "competition").casefold() == "competition"
            for item in sports
        )
        stage_sports = sum(
            str(item.get("type") or "").casefold() == "stage"
            for item in sports
        )
        return {
            "authenticated": True,
            "provider": active_provider.provider_id,
            "package": "prematch",
            "access_level": active_provider.client.access_level,
            "access_tier": active_provider.access_tier,
            "access_origin_id": active_provider.access_origin_id,
            "books_discovered": len(books),
            "sports_discovered": len(sports),
            "competition_based_sports": competition_sports,
            "stage_based_sports": stage_sports,
            "event_markets_collected": False,
            "api_key_logged": False,
            "interpretation": (
                "Access metadata is taken from the authenticated Books response. "
                "A successful Books request does not prove access to every package, "
                "competition, event, bookmaker or market."
            ),
        }
    finally:
        await active_provider.close()


def main() -> None:
    result = asyncio.run(inspect_access())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
