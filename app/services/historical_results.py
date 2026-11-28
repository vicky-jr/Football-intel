"""Historical event-result persistence with provenance and correction history."""
from __future__ import annotations
import json,sqlite3,uuid
from pathlib import Path
from typing import Any

class HistoricalResultsStore:
    def __init__(self,database_path:str|Path)->None:
        self.database_path=str(database_path)
        if self.database_path!=":memory:":Path(self.database_path).expanduser().parent.mkdir(parents=True,exist_ok=True)
        with self._connect() as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS event_results(
                result_id TEXT PRIMARY KEY,canonical_event_id TEXT NOT NULL,sport TEXT NOT NULL,
                outcome TEXT NOT NULL,result_payload_json TEXT NOT NULL,source_name TEXT NOT NULL,
                source_url TEXT,observed_at TEXT NOT NULL,verified INTEGER NOT NULL DEFAULT 0,
                supersedes_result_id TEXT);
              CREATE INDEX IF NOT EXISTS idx_event_results_event ON event_results(canonical_event_id,observed_at);
            """)
    def _connect(self):
        db=sqlite3.connect(self.database_path,timeout=30);db.row_factory=sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000");return db
    def record_result(self,*,canonical_event_id:str,sport:str,outcome:str,result_payload:dict[str,Any],
                      source_name:str,observed_at:str,source_url:str|None=None,verified:bool=False,
                      supersedes_result_id:str|None=None)->dict[str,Any]:
        if any(not x.strip() for x in (canonical_event_id,sport,outcome,source_name,observed_at)):
            raise ValueError("event, sport, outcome, source and timestamp are required")
        rid=str(uuid.uuid4())
        with self._connect() as db:
            if supersedes_result_id and not db.execute("SELECT 1 FROM event_results WHERE result_id=?",(supersedes_result_id,)).fetchone():
                raise KeyError("superseded result record not found")
            db.execute("""INSERT INTO event_results VALUES(?,?,?,?,?,?,?,?,?,?)""",
              (rid,canonical_event_id,sport,outcome,json.dumps(result_payload,ensure_ascii=False,default=str),
               source_name,source_url,observed_at,int(verified),supersedes_result_id))
        return {"result_id":rid,"canonical_event_id":canonical_event_id,"sport":sport,"outcome":outcome,
          "source_name":source_name,"source_url":source_url,"observed_at":observed_at,
          "verified":verified,"supersedes_result_id":supersedes_result_id}
    def get_event_results(self,canonical_event_id:str)->list[dict[str,Any]]:
        with self._connect() as db:rows=db.execute("SELECT * FROM event_results WHERE canonical_event_id=? ORDER BY observed_at DESC",(canonical_event_id,)).fetchall()
        return [{**dict(x),"result_payload":json.loads(x["result_payload_json"]),"verified":bool(x["verified"])} for x in rows]
