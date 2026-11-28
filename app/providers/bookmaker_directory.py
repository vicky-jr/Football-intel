"""Persistent bookmaker/operator discovery directory.

Directory entries are not proof of live integration, data rights or regional
availability. The optional SQLite backing store preserves operator research,
source-identity links and verification states across application restarts.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4


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


@dataclass(frozen=True)
class BookmakerSourceLink:
    """A bookmaker identity as exposed by a third-party data provider."""

    operator_id: str
    provider_id: str
    source_book_id: str
    source_book_name: str
    verification_status: str = "candidate"
    evidence_url: str | None = None
    last_checked_at: str | None = None
    notes: str = "Candidate name/ID association; not yet verified."


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
_SOURCE_LINK_STATES = {"candidate", "verified", "rejected"}


class BookmakerDirectory:
    """In-memory or SQLite-backed directory of bookmaker discovery candidates."""

    def __init__(
        self,
        profiles: Iterable[BookmakerProfile] | None = None,
        database_path: str | Path | None = None,
    ) -> None:
        raw_path = str(database_path) if database_path is not None else None
        # A separate SQLite :memory: connection per operation would lose the schema.
        self.database_path = raw_path if raw_path and raw_path != ":memory:" else None
        self._profiles: dict[str, BookmakerProfile] = {}
        self._source_links: dict[tuple[str, str, str], BookmakerSourceLink] = {}
        if self.database_path is not None:
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
        regions = tuple(sorted({
            region.strip().upper()
            for region in profile.supported_regions if region.strip()
        }))
        return BookmakerProfile(
            operator_id=operator_id,
            display_name=display_name,
            aliases=tuple(dict.fromkeys(
                alias.strip() for alias in profile.aliases if alias.strip()
            )),
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
        connection.execute("PRAGMA foreign_keys = ON")
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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS bookmaker_source_links (
                    operator_id TEXT NOT NULL REFERENCES bookmaker_directory(operator_id)
                        ON DELETE CASCADE,
                    provider_id TEXT NOT NULL,
                    source_book_id TEXT NOT NULL,
                    source_book_name TEXT NOT NULL,
                    verification_status TEXT NOT NULL,
                    evidence_url TEXT,
                    last_checked_at TEXT,
                    notes TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (operator_id, provider_id, source_book_id)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_bookmaker_source_provider "
                "ON bookmaker_source_links(provider_id, source_book_id)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS bookmaker_audit_log (
                    sequence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    audit_id TEXT NOT NULL UNIQUE,
                    recorded_at TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    before_json TEXT,
                    after_json TEXT,
                    evidence_url TEXT,
                    reason TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    entry_hash TEXT NOT NULL UNIQUE
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_bookmaker_audit_entity "
                "ON bookmaker_audit_log(entity_type, entity_id, sequence_id)"
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS bookmaker_audit_no_update
                BEFORE UPDATE ON bookmaker_audit_log
                BEGIN
                    SELECT RAISE(ABORT, 'bookmaker audit log is append-only');
                END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS bookmaker_audit_no_delete
                BEFORE DELETE ON bookmaker_audit_log
                BEGIN
                    SELECT RAISE(ABORT, 'bookmaker audit log is append-only');
                END
                """
            )


    @staticmethod
    def _audit_json(value: Any) -> str:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )

    @staticmethod
    def _audit_actor(actor_id: str) -> str:
        actor = str(actor_id).strip()
        if not actor or len(actor) > 128:
            raise ValueError("actor_id must contain between 1 and 128 characters")
        return actor

    @staticmethod
    def _safe_evidence_url(value: str | None) -> str | None:
        """Keep an evidence location while dropping query strings and credentials."""
        if not value:
            return None
        try:
            parsed = urlsplit(value.strip())
            hostname = parsed.hostname
            if parsed.scheme.casefold() not in {"http", "https"} or not hostname:
                return None
            port = parsed.port
            netloc = hostname if port is None else f"{hostname}:{port}"
            return urlunsplit((parsed.scheme.casefold(), netloc, parsed.path, "", ""))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _audit_digest(payload: dict[str, Any]) -> str:
        serialized = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _append_audit_event(
        self,
        connection: sqlite3.Connection,
        *,
        action: str,
        entity_type: str,
        entity_id: str,
        actor_id: str,
        reason: str,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
        evidence_url: str | None = None,
    ) -> None:
        actor = self._audit_actor(actor_id)
        explanation = str(reason).strip()
        if len(explanation) > 1000:
            raise ValueError("audit reason must not exceed 1000 characters")
        previous = connection.execute(
            "SELECT entry_hash FROM bookmaker_audit_log "
            "ORDER BY sequence_id DESC LIMIT 1"
        ).fetchone()
        previous_hash = previous["entry_hash"] if previous else "0" * 64
        recorded_at = datetime.now(timezone.utc).isoformat()
        audit_id = str(uuid4())
        safe_url = self._safe_evidence_url(evidence_url)
        payload = {
            "audit_id": audit_id,
            "recorded_at": recorded_at,
            "actor_id": actor,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "before": before,
            "after": after,
            "evidence_url": safe_url,
            "reason": explanation or "No reason supplied",
            "previous_hash": previous_hash,
        }
        entry_hash = self._audit_digest(payload)
        connection.execute(
            """
            INSERT INTO bookmaker_audit_log (
                audit_id, recorded_at, actor_id, action, entity_type, entity_id,
                before_json, after_json, evidence_url, reason, previous_hash, entry_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit_id, recorded_at, actor, action, entity_type, entity_id,
                self._audit_json(before) if before is not None else None,
                self._audit_json(after) if after is not None else None,
                safe_url, payload["reason"], previous_hash, entry_hash,
            ),
        )

    def audit_history(
        self,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return persisted audit events newest first; requires SQLite storage."""
        if self.database_path is None:
            raise RuntimeError("audit history requires persistent SQLite storage")
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        clauses = []
        parameters: list[Any] = []
        if entity_type:
            clauses.append("entity_type = ?")
            parameters.append(entity_type)
        if entity_id:
            clauses.append("entity_id = ?")
            parameters.append(entity_id)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        parameters.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT audit_id, recorded_at, actor_id, action, entity_type,
                       entity_id, before_json, after_json, evidence_url, reason,
                       previous_hash, entry_hash
                FROM bookmaker_audit_log
                {where}
                ORDER BY sequence_id DESC
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [
            {
                "audit_id": row["audit_id"],
                "recorded_at": row["recorded_at"],
                "actor_id": row["actor_id"],
                "action": row["action"],
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "before": json.loads(row["before_json"]) if row["before_json"] else None,
                "after": json.loads(row["after_json"]) if row["after_json"] else None,
                "evidence_url": row["evidence_url"],
                "reason": row["reason"],
                "previous_hash": row["previous_hash"],
                "entry_hash": row["entry_hash"],
            }
            for row in rows
        ]

    def audit_integrity_report(self) -> dict[str, Any]:
        """Check the complete SHA-256 chain for accidental or unauthorised edits."""
        if self.database_path is None:
            raise RuntimeError("audit integrity requires persistent SQLite storage")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT audit_id, recorded_at, actor_id, action, entity_type, entity_id,
                       before_json, after_json, evidence_url, reason, previous_hash,
                       entry_hash
                FROM bookmaker_audit_log
                ORDER BY sequence_id ASC
                """
            ).fetchall()
        previous_hash = "0" * 64
        broken_audit_id = None
        for row in rows:
            before = json.loads(row["before_json"]) if row["before_json"] else None
            after = json.loads(row["after_json"]) if row["after_json"] else None
            payload = {
                "audit_id": row["audit_id"],
                "recorded_at": row["recorded_at"],
                "actor_id": row["actor_id"],
                "action": row["action"],
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "before": before,
                "after": after,
                "evidence_url": row["evidence_url"],
                "reason": row["reason"],
                "previous_hash": row["previous_hash"],
            }
            expected_hash = self._audit_digest(payload)
            if row["previous_hash"] != previous_hash or row["entry_hash"] != expected_hash:
                broken_audit_id = row["audit_id"]
                break
            previous_hash = row["entry_hash"]
        return {
            "verified": broken_audit_id is None,
            "entry_count": len(rows),
            "first_broken_audit_id": broken_audit_id,
            "latest_entry_hash": previous_hash if rows and broken_audit_id is None else None,
            "integrity_scope": (
                "application-level append-only SQLite triggers and an ordered hash chain; "
                "not an externally anchored immutable or WORM audit service"
            ),
        }

    @staticmethod
    def _columns(profile: BookmakerProfile) -> tuple:
        return (
            profile.operator_id, profile.display_name,
            json.dumps(profile.aliases, ensure_ascii=False),
            profile.integration_status, profile.verification_status,
            json.dumps(profile.supported_regions), profile.notes,
            profile.parent_group, profile.official_website, profile.access_method,
            profile.terms_review_status, profile.evidence_url, profile.last_checked_at,
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

    @staticmethod
    def _source_link_from_row(row: sqlite3.Row) -> BookmakerSourceLink:
        return BookmakerSourceLink(
            operator_id=row["operator_id"],
            provider_id=row["provider_id"],
            source_book_id=row["source_book_id"],
            source_book_name=row["source_book_name"],
            verification_status=row["verification_status"],
            evidence_url=row["evidence_url"],
            last_checked_at=row["last_checked_at"],
            notes=row["notes"],
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

    def register(
        self,
        profile: BookmakerProfile,
        *,
        actor_id: str = "system:unspecified",
        reason: str = "Operator added to discovery directory",
    ) -> None:
        normalized = self._normalize(profile)
        actor = self._audit_actor(actor_id)
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
                self._append_audit_event(
                    connection,
                    action="operator.registered",
                    entity_type="operator",
                    entity_id=normalized.operator_id,
                    actor_id=actor,
                    reason=reason,
                    before=None,
                    after=asdict(normalized),
                    evidence_url=normalized.evidence_url,
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f"bookmaker already registered: {normalized.operator_id}"
            ) from exc

    def update(
        self,
        profile: BookmakerProfile,
        *,
        actor_id: str = "system:unspecified",
        reason: str = "Operator record reviewed",
    ) -> None:
        """Update an operator record and preserve the changed fields in the audit log."""
        normalized = self._normalize(profile)
        actor = self._audit_actor(actor_id)
        if self.database_path is None:
            if normalized.operator_id not in self._profiles:
                raise KeyError(
                    f"bookmaker is not in the discovery directory: {normalized.operator_id}"
                )
            self._profiles[normalized.operator_id] = normalized
            return
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM bookmaker_directory WHERE operator_id = ?",
                (normalized.operator_id,),
            ).fetchone()
            if row is None:
                raise KeyError(
                    f"bookmaker is not in the discovery directory: {normalized.operator_id}"
                )
            previous = asdict(self._from_row(row))
            updated = asdict(normalized)
            changed_before = {
                key: value for key, value in previous.items()
                if value != updated[key]
            }
            changed_after = {
                key: updated[key] for key in changed_before
            }
            connection.execute(
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
                    normalized.display_name, json.dumps(normalized.aliases, ensure_ascii=False),
                    normalized.integration_status, normalized.verification_status,
                    json.dumps(normalized.supported_regions), normalized.notes,
                    normalized.parent_group, normalized.official_website,
                    normalized.access_method, normalized.terms_review_status,
                    normalized.evidence_url, normalized.last_checked_at,
                    normalized.operator_id,
                ),
            )
            if changed_before:
                self._append_audit_event(
                    connection,
                    action="operator.updated",
                    entity_type="operator",
                    entity_id=normalized.operator_id,
                    actor_id=actor,
                    reason=reason,
                    before=changed_before,
                    after=changed_after,
                    evidence_url=normalized.evidence_url,
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
        links = self.list_source_links()
        return {
            "directory_count": len(profiles),
            "integration_status_counts": by_integration,
            "verification_status_counts": by_verification,
            "regions_with_recorded_support": sorted(known_regions),
            "source_identity_links": len(links),
            "verified_source_identity_links": sum(
                link["verification_status"] == "verified" for link in links
            ),
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

    def add_source_link(
        self,
        operator_id: str,
        provider_id: str,
        source_book_id: str,
        source_book_name: str,
        notes: str = "Candidate name/ID association; not yet verified.",
        *,
        actor_id: str = "system:unspecified",
        reason: str = "Provider-native source identity discovered",
    ) -> None:
        """Record a candidate source identity and preserve its provenance event."""
        operator = operator_id.strip().lower()
        provider = provider_id.strip().lower()
        source_id = source_book_id.strip()
        source_name = source_book_name.strip()
        if not provider or not source_id or not source_name:
            raise ValueError("provider_id, source_book_id and source_book_name are required")
        actor = self._audit_actor(actor_id)
        self.get(operator)
        link = BookmakerSourceLink(
            operator_id=operator,
            provider_id=provider,
            source_book_id=source_id,
            source_book_name=source_name,
            notes=notes.strip(),
        )
        key = (operator, provider, source_id)
        if self.database_path is None:
            if key in self._source_links:
                raise ValueError("source identity link already exists")
            self._source_links[key] = link
            return
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO bookmaker_source_links (
                        operator_id, provider_id, source_book_id, source_book_name,
                        verification_status, evidence_url, last_checked_at, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        link.operator_id, link.provider_id, link.source_book_id,
                        link.source_book_name, link.verification_status,
                        link.evidence_url, link.last_checked_at, link.notes,
                    ),
                )
                self._append_audit_event(
                    connection,
                    action="source_link.created",
                    entity_type="source_link",
                    entity_id=f"{operator}:{provider}:{source_id}",
                    actor_id=actor,
                    reason=reason,
                    before=None,
                    after=asdict(link),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("source identity link already exists") from exc

    def set_source_link_status(
        self,
        operator_id: str,
        provider_id: str,
        source_book_id: str,
        verification_status: str,
        evidence_url: str | None = None,
        last_checked_at: str | None = None,
        notes: str | None = None,
        *,
        actor_id: str = "system:unspecified",
        reason: str = "Source identity review state changed",
    ) -> None:
        """Change a source-link review state and audit the decision with evidence."""
        if verification_status not in _SOURCE_LINK_STATES:
            raise ValueError("unsupported source-link verification_status")
        actor = self._audit_actor(actor_id)
        operator = operator_id.strip().lower()
        provider = provider_id.strip().lower()
        source_id = source_book_id.strip()
        evidence = evidence_url.strip() if evidence_url else None
        checked = last_checked_at.strip() if last_checked_at else None
        if verification_status == "verified":
            if not evidence or not checked:
                raise ValueError(
                    "verified source links require evidence_url and last_checked_at"
                )
            if not evidence.startswith(("https://", "http://")):
                raise ValueError("evidence_url must be an HTTP(S) URL")
        key = (operator, provider, source_id)
        if self.database_path is None:
            try:
                current = self._source_links[key]
            except KeyError as exc:
                raise KeyError("source identity link was not found") from exc
            self._source_links[key] = BookmakerSourceLink(
                operator_id=current.operator_id,
                provider_id=current.provider_id,
                source_book_id=current.source_book_id,
                source_book_name=current.source_book_name,
                verification_status=verification_status,
                evidence_url=evidence or current.evidence_url,
                last_checked_at=checked or current.last_checked_at,
                notes=notes.strip() if notes is not None else current.notes,
            )
            return
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT * FROM bookmaker_source_links
                WHERE operator_id = ? AND provider_id = ? AND source_book_id = ?
                """,
                (operator, provider, source_id),
            ).fetchone()
            if existing is None:
                raise KeyError("source identity link was not found")
            previous = asdict(self._source_link_from_row(existing))
            updated = {
                **previous,
                "verification_status": verification_status,
                "evidence_url": evidence or previous["evidence_url"],
                "last_checked_at": checked or previous["last_checked_at"],
                "notes": notes.strip() if notes is not None else previous["notes"],
            }
            connection.execute(
                """
                UPDATE bookmaker_source_links SET
                    verification_status = ?,
                    evidence_url = COALESCE(?, evidence_url),
                    last_checked_at = COALESCE(?, last_checked_at),
                    notes = COALESCE(?, notes),
                    updated_at = CURRENT_TIMESTAMP
                WHERE operator_id = ? AND provider_id = ? AND source_book_id = ?
                """,
                (
                    verification_status, evidence, checked,
                    notes.strip() if notes is not None else None,
                    operator, provider, source_id,
                ),
            )
            changed_before = {
                key: value for key, value in previous.items()
                if value != updated[key]
            }
            changed_after = {
                key: updated[key] for key in changed_before
            }
            if changed_before:
                self._append_audit_event(
                    connection,
                    action=f"source_link.{verification_status}",
                    entity_type="source_link",
                    entity_id=f"{operator}:{provider}:{source_id}",
                    actor_id=actor,
                    reason=reason,
                    before=changed_before,
                    after=changed_after,
                    evidence_url=updated["evidence_url"],
                )

    def list_source_links(self, operator_id: str | None = None) -> list[dict]:
        """Return source-native bookmaker identities; candidate links remain unverified."""
        if operator_id is not None:
            operator = operator_id.strip().lower()
            self.get(operator)
        else:
            operator = None
        if self.database_path is None:
            links = list(self._source_links.values())
            if operator:
                links = [item for item in links if item.operator_id == operator]
        else:
            with self._connect() as connection:
                if operator:
                    rows = connection.execute(
                        """
                        SELECT * FROM bookmaker_source_links
                        WHERE operator_id = ?
                        ORDER BY provider_id, source_book_name
                        """,
                        (operator,),
                    ).fetchall()
                else:
                    rows = connection.execute(
                        """
                        SELECT * FROM bookmaker_source_links
                        ORDER BY operator_id, provider_id, source_book_name
                        """
                    ).fetchall()
            links = [self._source_link_from_row(row) for row in rows]
        return [asdict(link) for link in links]


    @staticmethod
    def _normalize_source_name(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value).casefold()
        return "".join(character for character in normalized if character.isalnum())

    def suggest_source_identity_matches(
        self, source_items: Iterable[dict]
    ) -> list[dict]:
        """Suggest exact normalized-name matches; never create or verify links."""
        name_index: dict[str, set[str]] = {}
        for profile in self._all_profiles():
            for name in (profile.display_name, *profile.aliases):
                key = self._normalize_source_name(name)
                if key:
                    name_index.setdefault(key, set()).add(profile.operator_id)

        suggestions: list[dict] = []
        for item in source_items:
            if not isinstance(item, dict):
                continue
            source_name = str(item.get("name") or item.get("label") or "").strip()
            source_id = item.get("source_id")
            provider_id = item.get("provider")
            normalized_name = self._normalize_source_name(source_name)
            candidates = sorted(name_index.get(normalized_name, set())) if normalized_name else []
            if len(candidates) == 1:
                state = "exact_name_candidate"
            elif len(candidates) > 1:
                state = "ambiguous"
            elif source_name:
                state = "unmatched"
            else:
                state = "missing_name"
            suggestions.append({
                "provider_id": provider_id,
                "source_book_id": str(source_id) if source_id is not None else None,
                "source_book_name": source_name or None,
                "suggestion_status": state,
                "candidate_operator_ids": candidates,
                "match_method": "normalized_exact_name" if candidates else None,
                "last_seen_at": item.get("captured_at"),
                "review_required": True,
            })
        return suggestions
