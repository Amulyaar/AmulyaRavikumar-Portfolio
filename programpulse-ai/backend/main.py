"""FastAPI service for the ProgramPulse AI synthetic delivery command center."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from engine import Store

DEFAULT_DB = Path(__file__).parent / "programpulse.db"
store = Store(os.environ.get("PROGRAMPULSE_DB", DEFAULT_DB))
app = FastAPI(title="ProgramPulse AI", version="1.0.0", description="Synthetic fintech TPM delivery simulator")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_credentials=False, allow_methods=["GET", "POST", "PATCH"], allow_headers=["*"])


class Escalation(BaseModel):
    status: Literal["Open", "Escalated", "Mitigating", "Resolved"]


@app.get("/api/health")
def health():
    return {"ok": True, "mode": "synthetic", "db": str(store.db_path)}


@app.get("/api/overview")
def overview():
    return store.overview()


@app.get("/api/tasks")
def tasks(team: Optional[str] = None, status: Optional[str] = None, search: Optional[str] = None,
          limit: int = Query(100, ge=1, le=500)):
    return {"items": store.tasks(team, status, search, limit), "limit": limit}


@app.get("/api/tasks/{task_id}")
def task(task_id: str):
    result = store.task(task_id)
    if result is None:
        raise HTTPException(404, "Task not found")
    return result


@app.get("/api/graph")
def graph(scope: Literal["all", "critical", "blockers"] = "critical"):
    analysis = store.dependency_analysis()
    if scope == "all":
        return analysis
    if scope == "critical":
        ids = set(analysis["critical_path"])
    else:
        blocked = set(analysis["blocked_downstream"])
        links = analysis["edges"]
        ids = blocked | {e["target"] for e in links if e["source"] in blocked}
    analysis["nodes"] = [n for n in analysis["nodes"] if n["id"] in ids]
    analysis["edges"] = [e for e in analysis["edges"] if e["source"] in ids and e["target"] in ids]
    return analysis


@app.get("/api/raid")
def raid(kind: Optional[str] = None, status: Optional[str] = None):
    return {"items": store.raid(kind, status)}


@app.patch("/api/raid/{item_id}")
def update_raid(item_id: str, update: Escalation):
    item = store.one("SELECT * FROM raid WHERE id=?", (item_id,))
    if not item:
        raise HTTPException(404, "RAID item not found")
    with store.connect() as conn:
        conn.execute("UPDATE raid SET status=? WHERE id=?", (update.status, item_id))
        conn.commit()
    return store.one("SELECT * FROM raid WHERE id=?", (item_id,))


@app.get("/api/reports/status")
def status_report():
    return store.status_report()


@app.get("/api/evidence/{reference:path}")
def evidence(reference: str):
    result = store.evidence(reference)
    if result is None:
        raise HTTPException(404, "Evidence not found")
    return {"reference": reference, "record": result}


@app.get("/api/export/tasks.csv")
def export_tasks():
    return PlainTextResponse(store.tasks_csv(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=programpulse-tasks.csv"})


@app.get("/api/export/status.json")
def export_report():
    return JSONResponse(store.status_report(), headers={"Content-Disposition": "attachment; filename=programpulse-status.json"})
