"""Persistent alert rules and cooldown-deduplicated alert events."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime,timezone
import json,sqlite3,uuid
from pathlib import Path
from typing import Iterator,Any

class AlertStore:
    def __init__(self,database_path:str|Path)->None:
        self.database_path=str(database_path)
        if self.database_path!=":memory:":Path(self.database_path).expanduser().parent.mkdir(parents=True,exist_ok=True)
        with self._connection() as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS alert_rules(
                rule_id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,provider_id TEXT NOT NULL,
                comparable_market_key TEXT NOT NULL,threshold_percent REAL NOT NULL,
                cooldown_seconds INTEGER NOT NULL,enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS alert_events(
                alert_id TEXT PRIMARY KEY,rule_id TEXT NOT NULL REFERENCES alert_rules(rule_id) ON DELETE CASCADE,
                dedupe_key TEXT NOT NULL,triggered_at TEXT NOT NULL,result_json TEXT NOT NULL);
              CREATE INDEX IF NOT EXISTS idx_alert_events_rule_time ON alert_events(rule_id,triggered_at);
            """)
    def _connect(self):
        db=sqlite3.connect(self.database_path,timeout=30);db.row_factory=sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON");db.execute("PRAGMA busy_timeout=30000");return db
    @contextmanager
    def _connection(self)->Iterator[sqlite3.Connection]:
        db=self._connect()
        try:yield db;db.commit()
        except Exception:db.rollback();raise
        finally:db.close()
    def create_rule(self,owner_id:str,provider_id:str,comparable_market_key:str,
                    threshold_percent:float=5.0,cooldown_seconds:int=900)->dict[str,Any]:
        if not owner_id.strip() or not provider_id.strip() or not comparable_market_key.strip():raise ValueError("owner, provider and market key are required")
        if threshold_percent<=0 or cooldown_seconds<0:raise ValueError("threshold must be positive and cooldown non-negative")
        rule_id=str(uuid.uuid4());now=datetime.now(timezone.utc).isoformat()
        with self._connection() as db:
            db.execute("INSERT INTO alert_rules VALUES(?,?,?,?,?,?,1,?)",
              (rule_id,owner_id,provider_id,comparable_market_key,threshold_percent,cooldown_seconds,now))
        return {"rule_id":rule_id,"owner_id":owner_id,"provider_id":provider_id,
          "comparable_market_key":comparable_market_key,"threshold_percent":threshold_percent,
          "cooldown_seconds":cooldown_seconds,"enabled":True,"created_at":now}
    def list_rules(self,owner_id:str)->list[dict[str,Any]]:
        with self._connection() as db:rows=db.execute("SELECT * FROM alert_rules WHERE owner_id=? ORDER BY created_at DESC",(owner_id,)).fetchall()
        return [{**dict(x),"enabled":bool(x["enabled"])} for x in rows]
    def set_enabled(self,rule_id:str,enabled:bool)->None:
        with self._connection() as db:
            cur=db.execute("UPDATE alert_rules SET enabled=? WHERE rule_id=?",(int(enabled),rule_id))
            if not cur.rowcount:raise KeyError("alert rule not found")
    def record_trigger(self,rule_id:str,dedupe_key:str,triggered_at:str,result:dict[str,Any])->dict[str,Any]:
        try:now=datetime.fromisoformat(triggered_at.replace("Z","+00:00"))
        except (ValueError,AttributeError) as exc:raise ValueError("triggered_at must be ISO timestamp with timezone") from exc
        if now.tzinfo is None or now.utcoffset() is None:raise ValueError("triggered_at must include timezone")
        now=now.astimezone(timezone.utc)
        with self._connection() as db:
            rule=db.execute("SELECT * FROM alert_rules WHERE rule_id=?",(rule_id,)).fetchone()
            if not rule:raise KeyError("alert rule not found")
            if not rule["enabled"]:return {"recorded":False,"reason":"rule_disabled"}
            previous=db.execute(
              "SELECT triggered_at FROM alert_events WHERE rule_id=? AND dedupe_key=? ORDER BY triggered_at DESC LIMIT 1",
              (rule_id,dedupe_key)).fetchone()
            if previous:
                last=datetime.fromisoformat(previous["triggered_at"].replace("Z","+00:00"))
                if (now-last).total_seconds()<rule["cooldown_seconds"]:
                    return {"recorded":False,"reason":"cooldown_active","cooldown_seconds":rule["cooldown_seconds"]}
            alert_id=str(uuid.uuid4())
            db.execute("INSERT INTO alert_events VALUES(?,?,?,?,?)",
              (alert_id,rule_id,dedupe_key,now.isoformat(),json.dumps(result,ensure_ascii=False,default=str)))
        return {"recorded":True,"alert_id":alert_id,"rule_id":rule_id,"triggered_at":now.isoformat()}
    def list_events(self,owner_id:str,limit:int=100)->list[dict[str,Any]]:
        if not 1<=limit<=500:raise ValueError("limit must be between 1 and 500")
        with self._connection() as db:
            rows=db.execute("""SELECT e.*,r.owner_id,r.provider_id,r.comparable_market_key
              FROM alert_events e JOIN alert_rules r ON r.rule_id=e.rule_id
              WHERE r.owner_id=? ORDER BY e.triggered_at DESC LIMIT ?""",(owner_id,limit)).fetchall()
        return [{**dict(x),"result":json.loads(x["result_json"])} for x in rows]
