"""Persistent bookmaker/operator discovery directory.

Directory entries are not proof of live integration, data rights or regional
availability. The optional SQLite backing store preserves operator research
and verification states across application restarts.
"""
from dataclasses import asdict, dataclass, replace
import json
import sqlite3
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class BookmakerProfile:
    operator_id: str
    display_name: str
    aliases: tuple[str, ...] = ()
    integration_status: str = "not_connected"
    verification_status: str = "not_verified"
    supported_regions: tuple[str, ...] = ()
    notes: str = "Discovery candidate only; access, terms and regional availability not verified."
    parent_group: str | None = None
    official_website: str | None = None
    access_method: str = "none"
    terms_review_status: str = "not_reviewed"
    evidence_url: str | None = None
    last_checked_at: str | None = None


# Seed names are discovery candidates, not claims of access or availability.
_SEED_OPERATORS = (
    ("1xbet", "1xBet", ("1xbet",)),
    ("paripesa", "PariPesa / Paripesa", ("paripesa",)),
    ("sportybet", "SportyBet", ("sporty bet",)),
    ("bet9ja", "Bet9ja", ()),
    ("betking", "BetKing", ()),
    ("betway", "Betway", ()),
    ("betano", "Betano", ()),
    ("stake", "Stake", ()),
    ("bet365", "bet365", ()),
    ("william-hill", "William Hill", ()),
    ("pinnacle", "Pinnacle", ()),
    ("unibet", "Unibet", ()),
    ("bwin", "Bwin", ()),
    ("888sport", "888sport", ("888 sport",)),
    ("draftkings", "DraftKings", ()),
    ("fanduel", "FanDuel", ()),
    ("betmgm", "BetMGM", ()),
    ("caesars", "Caesars", ()),
    ("betfair", "Betfair", ()),
    ("22bet", "22Bet", ()),
    ("betwinner", "BetWinner", ()),
    ("melbet", "MELbet", ()),
    ("mozzartbet", "MozzartBet", ()),
    ("betpawa", "betPawa", ()),
    ("msport", "MSport", ()),
)

_INTEGRATION_STATES = {
    "not_connected", "access_review", "authorised", "connected",
    "ingestion_verified", "temporarily_unavailable", "disabled",
}
_VERIFICATION_STATES = {
    "not_verified", "partially_verified", "verified", "rejected",
}
_ACCESS_METHODS = {
    "none", "official_api", "licensed_feed", "provider_approved_web",
    "user_provided", "other_authorized",
}
_TERMS_STATES = {
    "not_reviewed", "in_review", "approved", "restricted", "unclear",
}


class BookmakerDirectory:
    """In-memory or SQLite-backed directory of bookmaker discovery candidates."""

    def __init__(
        self,
        profiles: Iterable[BookmakerProfile] | None = None,
        database_path: str | Path | None = None,
    ) -> None:
        self.database_path = str(database_path) if database_path is not None else None
        self._profiles: dict[str, BookmakerProfile] = {}
        if self.database_path is not None:
            if self.database_path != ":memory:":
                Path(self.database_path).expanduser().parent.mkdir(
                    parents=True, exist_ok=True
                )
            self._initialize_database()
        initial_profiles = profiles if profiles is not None else self.seed_profiles()
        for profile in initial_profiles:
            if self.database_path is not None and profiles is None:
                self._insert_if_missing(profile)
            else:
                self.register(profile)

    @staticmethod
    def seed_profiles() -> tuple[BookmakerProfile, ...]:
        return tuple(
            BookmakerProfile(operator_id=operator_id, display_name=name, aliases=aliases)
            for operator_id, name, aliases in _SEED_OPERATORS
        )

    @staticmethod
    def _normalize(profile: BookmakerProfile) -> BookmakerProfile:
        operator_id = profile.operator_id.strip().lower()
        display_name = profile.display_name.strip()
        if not operator_id:
            raise ValueError("operator_id must be a non-empty stable identifier")
        if not display_name:
            raise ValueError("display_name must not be empty")
        if profile.integration_status not in _INTEGRATION_STATES:
            raise ValueError("unsupported integration_status")
        if profile.verification_status not in _VERIFICATION_STATES:
            raise ValueError("unsupported verification_status")
        if profile.access_method not in _ACCESS_METHODS:
            raise ValueError("unsupported access_method")
        if profile.terms_review_status not in _TERMS_STATES:
            raise ValueError("unsupported terms_review_status")
        regions = tuple(sorted({region.strip().upper() for region in profile.supported_regions if region.strip()}))
        return BookmakerProfile(
            operator_id=operator_id,
            display_name=display_name,
            aliases=tuple(dict.fromkeys(alias.strip() for alias in profile.aliases if alias.strip())),
            integration_status=profile.integration_status,
            verification_status=profile.verification_status,
            supported_regions=regions,
            notes=profile.notes.strip(),
            parent_group=profile.parent_group.strip() if profile.parent_group else None,
            official_website=profile.official_website.strip() if profile.official_website else None,
            access_method=profile.access_method,
            terms_review_status=profile.terms_review_status,
            evidence_url=profile.evidence_url.strip() if profile.evidence_url else None,
            last_checked_at=profile.last_checked_at.strip() if profile.last_checked_at else None,
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def _initialize_database(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS bookmaker_directory (
                    operator_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    aliases_json TEXT NOT NULL,
                    integration_status TEXT NOT NULL,
                    verification_status TEXT NOT NULL,
                    supported_regions_json TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    parent_group TEXT,
                    official_website TEXT,
                    access_method TEXT NOT NULL,
                    terms_review_status TEXT NOT NULL,
                    evidence_url TEXT,
                    last_checked_at TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_bookmaker_directory_name "
                "ON bookmaker_directory(display_name)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_bookmaker_directory_status "
                "ON bookmaker_directory(integration_status, verification_status)"
            )

    @staticmethod
    def _columns(profile: BookmakerProfile) -> tuple:
        return (
            profile.operator_id,
            profile.display_name,
            json.dumps(profile.aliases, ensure_ascii=False),
            profile.integration_status,
            profile.verification_status,
            json.dumps(profile.supported_regions),
            profile.notes,
            profile.parent_group,
            profile.official_website,
            profile.access_method,
            profile.terms_review_status,
            profile.evidence_url,
            profile.last_checked_at,
        )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> BookmakerProfile:
        return BookmakerProfile(
            operator_id=row["operator_id"],
            display_name=row["display_name"],
            aliases=tuple(json.loads(row["aliases_json"])),
            integration_status=row["integration_status"],
            verification_status=row["verification_status"],
            supported_regions=tuple(json.loads(row["supported_regions_json"])),
            notes=row["notes"],
            parent_group=row["parent_group"],
            official_website=row["official_website"],
            access_method=row["access_method"],
            terms_review_status=row["terms_review_status"],
            evidence_url=row["evidence_url"],
            last_checked_at=row["last_checked_at"],
        )

    def _insert_if_missing(self, profile: BookmakerProfile) -> None:
        normalized = self._normalize(profile)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO bookmaker_directory (
                    operator_id, display_name, aliases_json, integration_status,
                    verification_status, supported_regions_json, notes, parent_group,
                    official_website, access_method, terms_review_status,
                    evidence_url, last_checked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._columns(normalized),
            )

    def register(self, profile: BookmakerProfile) -> None:
        normalized = self._normalize(profile)
        if self.database_path is None:
            if normalized.operator_id in self._profiles:
                raise ValueError(f"bookmaker already registered: {normalized.operator_id}")
            self._profiles[normalized.operator_id] = normalized
            return
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO bookmaker_directory (
                        operator_id, display_name, aliases_json, integration_status,
                        verification_status, supported_regions_json, notes, parent_group,
                        official_website, access_method, terms_review_status,
                        evidence_url, last_checked_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._columns(normalized),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f"bookmaker already registered: {normalized.operator_id}"
            ) from exc

    def update(self, profile: BookmakerProfile) -> None:
        """Update an existing operator record; intended for trusted admin workflows."""
        normalized = self._normalize(profile)
        if self.database_path is None:
            if normalized.operator_id not in self._profiles:
                raise KeyError(f"bookmaker is not in the discovery directory: {normalized.operator_id}")
            self._profiles[normalized.operator_id] = normalized
            return
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE bookmaker_directory SET
                    display_name = ?, aliases_json = ?, integration_status = ?,
                    verification_status = ?, supported_regions_json = ?, notes = ?,
                    parent_group = ?, official_website = ?, access_method = ?,
                    terms_review_status = ?, evidence_url = ?, last_checked_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE operator_id = ?
                """,
                (
                    normalized.display_name,
                    json.dumps(normalized.aliases, ensure_ascii=False),
                    normalized.integration_status,
                    normalized.verification_status,
                    json.dumps(normalized.supported_regions),
                    normalized.notes,
                    normalized.parent_group,
                    normalized.official_website,
                    normalized.access_method,
                    normalized.terms_review_status,
                    normalized.evidence_url,
                    normalized.last_checked_at,
                    normalized.operator_id,
                ),
            )
            if cursor.rowcount == 0:
                raise KeyError(
                    f"bookmaker is not in the discovery directory: {normalized.operator_id}"
                )

    def _all_profiles(self) -> list[BookmakerProfile]:
        if self.database_path is None:
            return list(self._profiles.values())
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM bookmaker_directory ORDER BY display_name COLLATE NOCASE"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def list_profiles(
        self, query: str | None = None, region: str | None = None
    ) -> list[dict]:
        profiles = sorted(self._all_profiles(), key=lambda item: item.display_name.casefold())
        if query:
            needle = query.casefold().strip()
            profiles = [
                item for item in profiles
                if needle in item.display_name.casefold()
                or needle in item.operator_id.casefold()
                or any(needle in alias.casefold() for alias in item.aliases)
            ]
        if region:
            region_code = region.strip().upper()
            profiles = [
                item for item in profiles if region_code in item.supported_regions
            ]
        return [asdict(profile) for profile in profiles]

    def summary(self) -> dict:
        profiles = self._all_profiles()
        by_integration: dict[str, int] = {}
        by_verification: dict[str, int] = {}
        known_regions: set[str] = set()
        for profile in profiles:
            by_integration[profile.integration_status] = (
                by_integration.get(profile.integration_status, 0) + 1
            )
            by_verification[profile.verification_status] = (
                by_verification.get(profile.verification_status, 0) + 1
            )
            known_regions.update(profile.supported_regions)
        return {
            "directory_count": len(profiles),
            "integration_status_counts": by_integration,
            "verification_status_counts": by_verification,
            "regions_with_recorded_support": sorted(known_regions),
            "live_ingestion_verified": sum(
                p.integration_status == "ingestion_verified"
                and p.verification_status == "verified"
                for p in profiles
            ),
            "note": "A directory record is not proof of current regional availability or complete market coverage.",
        }

    def get(self, operator_id: str) -> BookmakerProfile:
        key = operator_id.strip().lower()
        if self.database_path is None:
            try:
                return self._profiles[key]
            except KeyError as exc:
                raise KeyError(
                    f"bookmaker is not in the discovery directory: {operator_id}"
                ) from exc
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM bookmaker_directory WHERE operator_id = ?", (key,)
            ).fetchone()
        if row is None:
            raise KeyError(
                f"bookmaker is not in the discovery directory: {operator_id}"
            )
        return self._from_row(row)
