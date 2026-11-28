"""Local ledger for user-entered exposure observations; no bookmaker account sync."""
from __future__ import annotations
import json,sqlite3,uuid
from pathlib import Path
from typing import Any

class RiskLedger:
    def __init__(self,database_path:str|Path)->None:
        self.database_path=str(database_path)
        if self.database_path!=":memory:":Path(self.database_path).expanduser().parent.mkdir(parents=True,exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS risk_entries(
              entry_id TEXT PRIMARY KEY,user_id TEXT NOT NULL,occurred_at TEXT NOT NULL,
              stake REAL NOT NULL,net_result REAL,status TEXT NOT NULL,metadata_json TEXT NOT NULL)""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_risk_entries_user_time ON risk_entries(user_id,occurred_at)")
    def _connect(self):
        db=sqlite3.connect(self.database_path,timeout=30);db.row_factory=sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000");return db
    def record(self,user_id:str,occurred_at:str,stake:float,status:str,
               net_result:float|None=None,metadata:dict[str,Any]|None=None)->dict[str,Any]:
        if not user_id.strip() or not occurred_at.strip() or stake<0:raise ValueError("valid user, timestamp and non-negative stake are required")
        eid=str(uuid.uuid4())
        with self._connect() as db:
            db.execute("INSERT INTO risk_entries VALUES(?,?,?,?,?,?,?)",
              (eid,user_id,occurred_at,stake,net_result,status,json.dumps(metadata or {},ensure_ascii=False,default=str)))
        return {"entry_id":eid,"user_id":user_id,"occurred_at":occurred_at,"stake":stake,"net_result":net_result,"status":status}
    def summary(self,user_id:str,since:str)->dict[str,Any]:
        with self._connect() as db:
            row=db.execute("""SELECT COUNT(*) entries,COALESCE(SUM(stake),0) stakes,
              COALESCE(SUM(CASE WHEN net_result<0 THEN -net_result ELSE 0 END),0) losses,
              COALESCE(SUM(CASE WHEN status IN ('open','pending') THEN stake ELSE 0 END),0) exposure
              FROM risk_entries WHERE user_id=? AND occurred_at>=?""",(user_id,since)).fetchone()
        return {"user_id":user_id,"since":since,"entries":row["entries"],"stakes":row["stakes"],
          "net_losses":row["losses"],"open_exposure":row["exposure"],"source":"user_entered_records",
          "coverage_warning":"This ledger is not connected to bookmaker accounts and may be incomplete."}
