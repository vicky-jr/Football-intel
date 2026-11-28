"""Durable SQLite storage for versioned bookmaker settlement-rule profiles."""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import asdict
import json,sqlite3
from pathlib import Path
from typing import Iterator
from app.services.settlement_rules import SettlementRuleProfile

class PersistentSettlementRuleRegistry:
    def __init__(self,database_path:str|Path)->None:
        self.database_path=str(database_path)
        if self.database_path!=":memory:":Path(self.database_path).expanduser().parent.mkdir(parents=True,exist_ok=True)
        with self._connection() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS settlement_profiles(
              profile_id TEXT PRIMARY KEY,provider_id TEXT NOT NULL,canonical_market_type_id TEXT NOT NULL,
              verification_status TEXT NOT NULL,profile_json TEXT NOT NULL)""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_settlement_profiles_provider ON settlement_profiles(provider_id)")
    def _connect(self):
        db=sqlite3.connect(self.database_path,timeout=30);db.row_factory=sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000");return db
    @contextmanager
    def _connection(self)->Iterator[sqlite3.Connection]:
        db=self._connect()
        try:yield db;db.commit()
        except Exception:db.rollback();raise
        finally:db.close()
    def register(self,profile:SettlementRuleProfile)->None:
        with self._connection() as db:
            try:
                db.execute("INSERT INTO settlement_profiles VALUES(?,?,?,?,?)",
                  (profile.profile_id,profile.provider_id,profile.canonical_market_type_id,
                   profile.verification_status,json.dumps(asdict(profile),ensure_ascii=False)))
            except sqlite3.IntegrityError as exc:raise ValueError(f"settlement profile already registered: {profile.profile_id}") from exc
    def get(self,profile_id:str)->SettlementRuleProfile:
        with self._connection() as db:row=db.execute("SELECT profile_json FROM settlement_profiles WHERE profile_id=?",(profile_id,)).fetchone()
        if not row:raise KeyError(f"settlement profile not found: {profile_id}")
        return SettlementRuleProfile(**json.loads(row["profile_json"]))
    def list_profiles(self)->list[dict]:
        with self._connection() as db:rows=db.execute("SELECT profile_json FROM settlement_profiles ORDER BY profile_id").fetchall()
        return [json.loads(x["profile_json"]) for x in rows]
