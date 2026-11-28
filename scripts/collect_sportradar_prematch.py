"""Run one authorised Sportradar Prematch collection scan.

Usage:
  SPORTRADAR_ODDS_API_KEY=... python scripts/collect_sportradar_prematch.py 2026-11-28

The API key is read from the environment and is never printed or persisted.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from datetime import datetime, timezone

from app.providers.registry import ProviderRegistry
from app.providers.sportradar import provider_from_environment
from app.services.ingestion import IngestionOrchestrator
from app.services.market_inventory import MarketInventory
from app.services.sqlite_store import SQLiteMarketStore


async def run(scan_date: str) -> dict:
    provider = provider_from_environment()
    store = SQLiteMarketStore()
    orchestrator = IngestionOrchestrator(
        ProviderRegistry([provider]),
        MarketInventory(),
        store=store,
        max_concurrency=4,
        max_retries=3,
        retry_delay_seconds=1.0,
    )
    try:
        report = await orchestrator.scan(
            provider.provider_id, scan_date, package="prematch"
        )
        return {
            "report": {
                **asdict(report),
                "started_at": report.started_at.isoformat(),
                "completed_at": report.completed_at.isoformat() if report.completed_at else None,
                "complete": report.complete,
            },
            "access_tier": provider.access_tier,
            "access_origin_id": provider.access_origin_id,
            "configured_book_count": len(provider._books_cache or []),
            "limitations": [
                "The scan covers only this API key's configured bookmakers and the Prematch package.",
                "OC Core must be enabled by Sportradar Support for global-core coverage.",
                "This scan does not include Player Props, Futures, Live Odds or bookmaker-hosted proprietary games.",
                "Verify data licensing, regional access, storage and redistribution rights before public display.",
            ],
        }
    finally:
        await provider.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect a Sportradar Prematch date window")
    parser.add_argument(
        "scan_date",
        nargs="?",
        default=datetime.now(timezone.utc).date().isoformat(),
        help="UTC date in YYYY-MM-DD format (the source schedule spans this date and the next)",
    )
    args = parser.parse_args()
    datetime.strptime(args.scan_date, "%Y-%m-%d")
    result = asyncio.run(run(args.scan_date))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
