"""HTTP API and static dashboard for LedgerGuard."""
from __future__ import annotations

import csv
import io
import os
from pathlib import Path
from threading import RLock
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .data import generate_invoices
from .engine import build_report, evaluate_invoices
from .storage import SnapshotStore

RUN_ID = "demo-2027-09-15"
WEB_DIR = Path(__file__).resolve().parent.parent / "web"
store = SnapshotStore()
lock = RLock()
app = FastAPI(title="LedgerGuard", version="1.0.0", description="Synthetic financial release-readiness simulator")


class StatusUpdate(BaseModel):
    status: str = Field(pattern="^(Open|Investigating|Resolved|Accepted)$")


def _snapshot() -> dict:
    with lock:
        saved = store.load(RUN_ID)
        if saved is None:
            saved = {"invoices": generate_invoices(), "statuses": {}}
            store.save(RUN_ID, saved)
        return saved


def _assessment() -> dict:
    data = _snapshot()
    return evaluate_invoices(data["invoices"], data["statuses"])


@app.get("/api/health")
def health():
    return {"status": "ok", "run_id": RUN_ID, "storage": "configured"}


@app.get("/api/overview")
def overview():
    assessment = _assessment()
    return {k: v for k, v in assessment.items() if k != "findings"}


@app.get("/api/findings")
def findings(severity: str | None = None, status: str | None = None, search: str = "", limit: int = Query(250, ge=1, le=1000)):
    rows = _assessment()["findings"]
    if severity:
        rows = [f for f in rows if f["severity"].lower() == severity.lower()]
    if status:
        rows = [f for f in rows if f["status"].lower() == status.lower()]
    needle = search.strip().lower()
    if needle:
        rows = [f for f in rows if needle in " ".join(str(f.get(k, "")) for k in ("finding_id", "invoice_id", "title", "owner_team", "rule_id")).lower()]
    return {"items": rows[:limit], "total": len(rows)}


@app.get("/api/invoices")
def invoices(search: str = "", limit: int = Query(100, ge=1, le=1000)):
    rows = _snapshot()["invoices"]
    if search.strip():
        needle = search.strip().lower()
        rows = [i for i in rows if needle in (i["invoice_id"] + " " + i["vendor_id"] + " " + i["invoice_number"]).lower()]
    return {"items": rows[:limit], "total": len(rows)}


@app.get("/api/invoices/{invoice_id}")
def invoice_detail(invoice_id: str):
    item = next((i for i in _snapshot()["invoices"] if i["invoice_id"] == invoice_id), None)
    if not item:
        raise HTTPException(404, "Invoice not found")
    related = [f for f in _assessment()["findings"] if f["invoice_id"] == invoice_id]
    return {"invoice": item, "findings": related}


@app.patch("/api/findings/{finding_id}/status")
def update_status(finding_id: str, body: StatusUpdate):
    current = _assessment()
    if not any(f["finding_id"] == finding_id for f in current["findings"]):
        raise HTTPException(404, "Finding not found")
    with lock:
        snapshot = _snapshot()
        snapshot["statuses"][finding_id] = body.status
        store.save(RUN_ID, snapshot)
    return {"finding_id": finding_id, "status": body.status, "overview": overview()}


@app.get("/api/report")
def report():
    return build_report(_assessment())


@app.get("/api/evidence/{reference}")
def evidence(reference: str):
    assessment = _assessment()
    if reference.startswith("finding:"):
        key = reference.partition(":")[2]
        result = next((f for f in assessment["findings"] if f["finding_id"] == key), None)
    elif reference.startswith("invoice:"):
        key = reference.partition(":")[2]
        result = next((i for i in _snapshot()["invoices"] if i["invoice_id"] == key), None)
    elif reference.startswith("metric:"):
        result = assessment.get(reference.partition(":")[2])
    elif reference.startswith("benchmark:"):
        key = reference.partition(":")[2]
        result = {"metric": key, "value": assessment.get(key), "truth_source": "ground_truth_defects labels embedded in fixed-seed synthetic fixtures"}
    else:
        raise HTTPException(400, "Unsupported evidence reference")
    if result is None:
        raise HTTPException(404, "Evidence not found")
    return {"reference": reference, "evidence": result}


@app.get("/api/export/findings.csv")
def export_findings():
    rows = _assessment()["findings"]
    out = io.StringIO()
    cols = ["finding_id", "invoice_id", "severity", "status", "title", "owner_team", "rule_id", "message"]
    writer = csv.DictWriter(out, fieldnames=cols)
    writer.writeheader()
    writer.writerows({key: row.get(key) for key in cols} for row in rows)
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=ledgerguard-findings.csv"})


@app.get("/")
def dashboard():
    return FileResponse(WEB_DIR / "index.html")


app.mount("/assets", StaticFiles(directory=WEB_DIR), name="assets")
