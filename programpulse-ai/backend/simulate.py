"""Deterministic, clearly synthetic TPM delivery data for ProgramPulse AI."""
from __future__ import annotations

import json
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

AS_OF = date(2027, 7, 15)
START = date(2027, 6, 2)
RELEASE = date(2027, 8, 27)
TEAMS = ["Platform", "Payments", "Risk & Identity", "Data", "Mobile"]
WORK = {
    "Platform": ["API gateway", "partner authentication", "service contracts", "observability", "feature flags"],
    "Payments": ["settlement ledger", "payment routing", "refund flow", "reconciliation", "payout orchestration"],
    "Risk & Identity": ["identity checks", "fraud rules", "decision service", "KYC review", "policy controls"],
    "Data": ["event stream", "quality checks", "metrics model", "warehouse sync", "audit exports"],
    "Mobile": ["onboarding flow", "checkout UI", "account alerts", "accessibility", "release build"],
}
MILESTONES = [
    ("M-01", "Partner contract locked", "2027-06-25", "Platform"),
    ("M-02", "Identity controls signed off", "2027-07-23", "Risk & Identity"),
    ("M-03", "Settlement reconciliation stable", "2027-08-04", "Payments"),
    ("M-04", "End-to-end staging verified", "2027-08-13", "Data"),
    ("M-05", "Release candidate approved", "2027-08-23", "Mobile"),
    ("M-06", "Pilot launch", "2027-08-27", "Platform"),
]
INCIDENTS = [
    ("R-001", "risk", "Critical", "Risk & Identity", "Identity API p95 latency above 350 ms gate", "Open", "2027-07-17", "T-0179", "Partner sandbox p95 reached 418 ms; optimize cache and rerun 10k-request test."),
    ("R-002", "blocker", "Critical", "Payments", "Settlement schema drift blocks reconciliation", "Escalated", "2027-07-16", "T-0234", "Partner payload renamed net_amount; contract review and adapter patch required."),
    ("R-003", "risk", "High", "Platform", "Partner authentication contract awaiting signature", "Open", "2027-07-18", "T-0128", "Legal redlines unresolved; integration owner needs signed v3 contract."),
    ("R-004", "issue", "High", "Data", "Staging audit export missing two required fields", "Mitigating", "2027-07-20", "T-0297", "Audit sample omitted jurisdiction and consent timestamp."),
    ("R-005", "decision", "Medium", "Mobile", "Choose biometric fallback for pilot cohort", "Pending", "2027-07-24", "T-0354", "Product and Risk to decide on passcode fallback for unsupported devices."),
    ("R-006", "risk", "Medium", "Payments", "Refund idempotency load test incomplete", "Open", "2027-07-27", "T-0414", "Need a replay run at twice projected pilot traffic."),
    ("R-007", "assumption", "Low", "Data", "Pilot event volume stays below 2M/day", "Accepted", "2027-08-01", "T-0342", "Capacity estimate based on 50k pilot users and 40 events per user."),
    ("R-008", "issue", "Medium", "Platform", "Feature flag rollback runbook needs dry run", "Mitigating", "2027-07-29", "T-0388", "On-call handoff drafted; one staging exercise remains."),
    ("R-009", "risk", "High", "Mobile", "Checkout accessibility regression", "Open", "2027-07-22", "T-0436", "Screen reader focus skips confirmation banner on iOS."),
    ("R-010", "decision", "Low", "Risk & Identity", "Pilot fraud threshold sign-off", "Approved", "2027-07-11", "T-0119", "Risk approved 0.72 review threshold for synthetic pilot cohort."),
    ("R-011", "issue", "Medium", "Data", "CDC backfill lag exceeded 15 minutes", "Resolved", "2027-07-09", "T-0167", "Index change reduced synthetic staging backfill lag to 8 minutes."),
    ("R-012", "assumption", "Low", "Platform", "Partner sandbox available during test window", "Accepted", "2027-08-08", "T-0443", "Partner confirmed weekday test access in simulation."),
    ("R-013", "risk", "Medium", "Mobile", "App store review may delay pilot rollout", "Open", "2027-08-19", "T-0476", "Submit candidate five business days before pilot."),
    ("R-014", "decision", "Medium", "Payments", "Use dual-write during ledger migration", "Approved", "2027-07-06", "T-0134", "Architecture review approved 48-hour dual-write window."),
    ("R-015", "issue", "Low", "Risk & Identity", "KYC copy mismatch between web and mobile", "Resolved", "2027-07-08", "T-0149", "Shared content token corrected in staging."),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tasks (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, team TEXT NOT NULL, owner TEXT NOT NULL,
 wave INTEGER NOT NULL, start_date TEXT NOT NULL, due_date TEXT NOT NULL,
 duration_days INTEGER NOT NULL, status TEXT NOT NULL, progress INTEGER NOT NULL,
 priority TEXT NOT NULL, milestone_id TEXT, scenario TEXT NOT NULL DEFAULT 'baseline'
);
CREATE TABLE IF NOT EXISTS dependencies (
 predecessor_id TEXT NOT NULL, successor_id TEXT NOT NULL,
 PRIMARY KEY (predecessor_id, successor_id)
);
CREATE TABLE IF NOT EXISTS milestones (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, due_date TEXT NOT NULL,
 team TEXT NOT NULL, status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS raid (
 id TEXT PRIMARY KEY, kind TEXT NOT NULL, severity TEXT NOT NULL,
 team TEXT NOT NULL, title TEXT NOT NULL, status TEXT NOT NULL,
 due_date TEXT NOT NULL, task_id TEXT NOT NULL, evidence TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_team_status ON tasks(team,status);
CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_raid_status ON raid(status,severity);
"""


def seed(db_path: str | Path, force: bool = False) -> dict:
    """Create one reproducible scenario. Existing data is preserved unless force=True."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if force and db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]:
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        conn.close()
        return {"tasks": count, "created": False}

    rng = random.Random(2027)
    owners = {
        "Platform": ["A. Chen", "M. Brooks", "S. Rao"],
        "Payments": ["J. Patel", "N. Garcia", "D. King"],
        "Risk & Identity": ["L. Kim", "R. Shah", "T. Morris"],
        "Data": ["E. Park", "P. Singh", "K. Rivera"],
        "Mobile": ["C. Lee", "F. Wilson", "B. Ahmed"],
    }
    rows = []
    deps = set()
    # Twenty delivery waves, five tasks per team per wave. Dependencies point only backwards.
    for wave in range(20):
        for team_idx, team in enumerate(TEAMS):
            for slot in range(5):
                index = wave * 25 + team_idx * 5 + slot + 1
                task_id = f"T-{index:04d}"
                workstream = WORK[team][slot]
                phase = ["Design", "Build", "Integrate", "Validate", "Harden"][wave % 5]
                start = START + timedelta(days=wave * 4 + rng.randint(0, 2))
                duration = rng.randint(2, 6)
                due = start + timedelta(days=duration)
                progress = max(0, min(100, int((AS_OF - start).days / max(duration, 1) * 100)))
                if progress >= 100:
                    status = "Done" if rng.random() > 0.12 else "In review"
                    progress = 100 if status == "Done" else 85
                elif progress > 0:
                    status = "In progress"
                    progress = max(10, min(90, progress))
                else:
                    status = "Not started"
                    progress = 0
                if rng.random() < 0.06 and due < AS_OF and status != "Done":
                    status = "Blocked"
                priority = "High" if (slot == 0 or wave in (8, 15, 19)) else "Medium"
                milestone_id = MILESTONES[min(wave // 4, 5)][0]
                rows.append((task_id, f"{phase} {workstream} · wave {wave + 1:02d}", team,
                             owners[team][(wave + slot) % 3], wave, start.isoformat(),
                             due.isoformat(), duration, status, progress, priority, milestone_id, "baseline"))
                if wave > 0:
                    prev = (wave - 1) * 25 + team_idx * 5 + slot + 1
                    deps.add((f"T-{prev:04d}", task_id))
                    if slot in (0, 3) and wave % 2 == 0:
                        cross_team = (wave - 1) * 25 + ((team_idx - 1) % 5) * 5 + slot + 1
                        deps.add((f"T-{cross_team:04d}", task_id))
                if slot > 0 and wave % 3 == 0:
                    deps.add((f"T-{index-1:04d}", task_id))

    # Inject named failures into the synthetic snapshot; these are the report's evidence anchors.
    failure_ids = {"T-0179": "Blocked", "T-0234": "Blocked", "T-0128": "Blocked",
                   "T-0297": "In review", "T-0436": "Blocked"}
    rows = [tuple(list(row[:8]) + [failure_ids[row[0]], 45 if row[0] in failure_ids else row[9]] + list(row[10:]))
            if row[0] in failure_ids else row for row in rows]

    conn.executemany("INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.executemany("INSERT INTO dependencies VALUES (?,?)", sorted(deps))
    for mid, name, due, team in MILESTONES:
        status = "Complete" if date.fromisoformat(due) < AS_OF and mid == "M-01" else "At risk" if mid in ("M-02", "M-03", "M-04") else "Upcoming"
        conn.execute("INSERT INTO milestones VALUES (?,?,?,?,?)", (mid, name, due, team, status))
    conn.executemany("INSERT INTO raid VALUES (?,?,?,?,?,?,?,?,?,?)",
                     [(*incident, AS_OF.isoformat()) for incident in INCIDENTS])
    conn.executemany("INSERT INTO metadata VALUES (?,?)", [
        ("seed", "2027"), ("as_of", AS_OF.isoformat()), ("release", RELEASE.isoformat()),
        ("scenario", "Synthetic fintech pilot; all people and incidents are fictional"),
    ])
    conn.commit()
    result = {"tasks": len(rows), "dependencies": len(deps), "raid": len(INCIDENTS), "created": True}
    conn.close()
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(Path(__file__).parent / "programpulse.db"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    print(json.dumps(seed(args.db, args.force), indent=2))
