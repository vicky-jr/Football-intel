"""Local analyst workspace for projects, evidence-linked notes and watchlists."""
from __future__ import annotations
import json,sqlite3,uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any,Iterator

class AnalystWorkspaceStore:
    """Local MVP storage; authentication and tenant authorisation are required before public use."""
    def __init__(self,database_path:str|Path)->None:
        self.database_path=str(database_path)
        if self.database_path!=":memory:":Path(self.database_path).expanduser().parent.mkdir(parents=True,exist_ok=True)
        with self._connection() as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS analyst_projects(
                project_id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,name TEXT NOT NULL,
                description TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
              CREATE TABLE IF NOT EXISTS analyst_notes(
                note_id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES analyst_projects(project_id) ON DELETE CASCADE,
                title TEXT NOT NULL,body TEXT NOT NULL,evidence_ids_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
              CREATE TABLE IF NOT EXISTS analyst_watchlist(
                project_id TEXT NOT NULL REFERENCES analyst_projects(project_id) ON DELETE CASCADE,
                item_key TEXT NOT NULL,item_type TEXT NOT NULL,label TEXT NOT NULL,
                PRIMARY KEY(project_id,item_key));
            """)
    @contextmanager
    def _connection(self)->Iterator[sqlite3.Connection]:
        db=self._connect()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    def _connect(self):
        db=sqlite3.connect(self.database_path,timeout=30);db.row_factory=sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON");db.execute("PRAGMA busy_timeout=30000");return db
    def create_project(self,owner_id:str,name:str,description:str="")->dict[str,Any]:
        if not owner_id.strip() or not name.strip():raise ValueError("owner_id and project name are required")
        pid=str(uuid.uuid4())
        with self._connection() as db:
            db.execute("INSERT INTO analyst_projects(project_id,owner_id,name,description) VALUES(?,?,?,?)",
                       (pid,owner_id,name.strip(),description))
        return {"project_id":pid,"owner_id":owner_id,"name":name.strip(),"description":description}
    def list_projects(self,owner_id:str)->list[dict[str,Any]]:
        with self._connection() as db:rows=db.execute("SELECT * FROM analyst_projects WHERE owner_id=? ORDER BY created_at DESC",(owner_id,)).fetchall()
        return [dict(x) for x in rows]
    def add_note(self,project_id:str,title:str,body:str,evidence_ids:list[str]|None=None)->dict[str,Any]:
        if not title.strip() or not body.strip():raise ValueError("note title and body are required")
        nid=str(uuid.uuid4())
        with self._connection() as db:
            if not db.execute("SELECT 1 FROM analyst_projects WHERE project_id=?",(project_id,)).fetchone():raise KeyError("project not found")
            db.execute("INSERT INTO analyst_notes(note_id,project_id,title,body,evidence_ids_json) VALUES(?,?,?,?,?)",
                       (nid,project_id,title.strip(),body,json.dumps(evidence_ids or [])))
        return {"note_id":nid,"project_id":project_id,"title":title.strip(),"body":body,"evidence_ids":evidence_ids or []}
    def list_notes(self,project_id:str)->list[dict[str,Any]]:
        with self._connection() as db:rows=db.execute("SELECT * FROM analyst_notes WHERE project_id=? ORDER BY created_at DESC",(project_id,)).fetchall()
        return [{**dict(x),"evidence_ids":json.loads(x["evidence_ids_json"])} for x in rows]
    def add_watchlist_item(self,project_id:str,item_key:str,item_type:str,label:str)->dict[str,Any]:
        with self._connection() as db:
            if not db.execute("SELECT 1 FROM analyst_projects WHERE project_id=?",(project_id,)).fetchone():
                raise KeyError("project not found")
            db.execute("INSERT OR REPLACE INTO analyst_watchlist(project_id,item_key,item_type,label) VALUES(?,?,?,?)",
                       (project_id,item_key,item_type,label))
        return {"project_id":project_id,"item_key":item_key,"item_type":item_type,"label":label}
    def list_watchlist(self,project_id:str)->list[dict[str,Any]]:
        with self._connection() as db:rows=db.execute("SELECT item_key,item_type,label FROM analyst_watchlist WHERE project_id=? ORDER BY item_type,item_key",(project_id,)).fetchall()
        return [dict(x) for x in rows]
