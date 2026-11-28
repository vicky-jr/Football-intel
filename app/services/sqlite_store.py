"""SQLite persistence for timestamped provider market observations.

SQLite is the local-development persistence backend. The interface is deliberately
small so a managed PostgreSQL implementation can replace it without changing
provider adapters or the ingestion orchestration contract.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any

from app.providers.base import ProviderEvent
from app.services.ingestion import IngestionReport
from app.services.market_inventory import EventMarketSnapshot


class SQLiteMarketStore:
    """Persist scan history, provider events and loss-aware market snapshots."""

    def __init__(self, database_path: str | Path = "data/football_intel.sqlite3") -> None:
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;

                CREATE TABLE IF NOT EXISTS scan_runs (
                    scan_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    scan_date TEXT NOT NULL,
                    package TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    status TEXT NOT NULL,
                    report_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS scan_failures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id TEXT NOT NULL REFERENCES scan_runs(scan_id) ON DELETE CASCADE,
                    stage TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    message TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS provider_events (
                    provider TEXT NOT NULL,
                    source_event_id TEXT NOT NULL,
                    sport TEXT NOT NULL,
                    competition TEXT,
                    name TEXT NOT NULL,
                    start_time TEXT,
                    status TEXT,
                    raw_json TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    PRIMARY KEY (provider, source_event_id)
                );

                CREATE TABLE IF NOT EXISTS market_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id TEXT NOT NULL REFERENCES scan_runs(scan_id) ON DELETE CASCADE,
                    provider TEXT NOT NULL,
                    source_event_id TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    markets_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_market_snapshots_event_time
                    ON market_snapshots(provider, source_event_id, captured_at);
                CREATE INDEX IF NOT EXISTS idx_market_snapshots_scan
                    ON market_snapshots(scan_id);
                CREATE INDEX IF NOT EXISTS idx_scan_runs_provider_date
                    ON scan_runs(provider, scan_date);
                """
            )

    @staticmethod
    def _json(value: Any) -> str:
        # Provider payloads are JSON in normal operation. default=str keeps an
        # unexpected adapter value diagnosable instead of losing the whole scan.
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)

    def start_scan(
        self,
        scan_id: str,
        provider: str,
        scan_date: str,
        package: str,
        started_at: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO scan_runs
                    (scan_id, provider, scan_date, package, started_at, status, report_json)
                VALUES (?, ?, ?, ?, ?, 'running', '{}')
                """,
                (scan_id, provider, scan_date, package, started_at),
            )

    def record_event(self, event: ProviderEvent, seen_at: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO provider_events (
                    provider, source_event_id, sport, competition, name,
                    start_time, status, raw_json, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider, source_event_id) DO UPDATE SET
                    sport=excluded.sport,
                    competition=excluded.competition,
                    name=excluded.name,
                    start_time=excluded.start_time,
                    status=excluded.status,
                    raw_json=excluded.raw_json,
                    last_seen_at=excluded.last_seen_at
                """,
                (
                    event.provider, event.source_event_id, event.sport,
                    event.competition, event.name, event.start_time, event.status,
                    self._json(event.raw), seen_at,
                ),
            )

    def record_snapshot(self, snapshot: EventMarketSnapshot, scan_id: str) -> None:
        markets = []
        for market in snapshot.markets:
            payload = asdict(market)
            # Preserve each source selection and its raw provider payload.
            markets.append(payload)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO market_snapshots
                    (scan_id, provider, source_event_id, captured_at, markets_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    scan_id, snapshot.provider, snapshot.source_event_id,
                    snapshot.captured_at.isoformat(), self._json(markets),
                ),
            )

    def finish_scan(self, scan_id: str, report: IngestionReport) -> None:
        report_data = {
            "books_discovered": report.books_discovered,
            "sports_discovered": report.sports_discovered,
            "competitions_discovered": report.competitions_discovered,
            "events_discovered": report.events_discovered,
            "events_scanned": report.events_scanned,
            "market_snapshots_recorded": report.market_snapshots_recorded,
            "markets_received": report.markets_received,
            "selections_received": report.selections_received,
            "failures": [asdict(failure) for failure in report.failures],
        }
        status = "complete" if report.complete else "partial"
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE scan_runs
                SET completed_at = ?, status = ?, report_json = ?
                WHERE scan_id = ?
                """,
                (
                    report.completed_at.isoformat() if report.completed_at else None,
                    status, self._json(report_data), scan_id,
                ),
            )
            connection.execute("DELETE FROM scan_failures WHERE scan_id = ?", (scan_id,))
            connection.executemany(
                """
                INSERT INTO scan_failures (scan_id, stage, scope, message)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (scan_id, failure.stage, failure.scope, failure.message)
                    for failure in report.failures
                ],
            )

    def coverage_report(self) -> dict[str, Any]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT provider, source_event_id, captured_at, markets_json
                FROM market_snapshots ORDER BY captured_at
                """
            ).fetchall()

        providers: dict[str, dict[str, Any]] = {}
        for row in rows:
            stats = providers.setdefault(
                row["provider"],
                {
                    "events_scanned": 0,
                    "snapshots": 0,
                    "markets_received": 0,
                    "selections_received": 0,
                    "unclassified_markets": 0,
                    "last_captured_at": None,
                },
            )
            markets = json.loads(row["markets_json"])
            stats["snapshots"] += 1
            stats["markets_received"] += len(markets)
            stats["selections_received"] += sum(
                len(market.get("selections", [])) for market in markets
            )
            stats["unclassified_markets"] += sum(
                not market.get("classified", False) for market in markets
            )
            stats["last_captured_at"] = row["captured_at"]
            stats.setdefault("_event_ids", set()).add(row["source_event_id"])

        for stats in providers.values():
            event_ids = stats.pop("_event_ids")
            stats["events_scanned"] = len(event_ids)

        return {"providers": providers, "snapshot_count": len(rows)}

    def scan_history(self, limit: int = 50) -> list[dict[str, Any]]:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT scan_id, provider, scan_date, package, started_at,
                       completed_at, status, report_json
                FROM scan_runs ORDER BY started_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "scan_id": row["scan_id"],
                "provider": row["provider"],
                "scan_date": row["scan_date"],
                "package": row["package"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
                "status": row["status"],
                "report": json.loads(row["report_json"]),
            }
            for row in rows
        ]
