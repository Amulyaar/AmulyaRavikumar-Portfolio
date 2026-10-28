"""Query, schedule, and evidence-grounded reporting functions."""
from __future__ import annotations

import csv
import io
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from simulate import AS_OF, RELEASE, TEAMS, seed

ACTIVE_RAID = {"Open", "Escalated", "Mitigating", "Pending"}
SEVERITY_WEIGHT = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}


class Store:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        seed(self.db_path)

    def connect(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def rows(self, sql, args=()):
        with self.connect() as conn:
            return [dict(row) for row in conn.execute(sql, args)]

    def one(self, sql, args=()):
        rows = self.rows(sql, args)
        return rows[0] if rows else None

    def tasks(self, team=None, status=None, search=None, limit=500):
        clauses, args = [], []
        if team:
            clauses.append("team = ?")
            args.append(team)
        if status:
            clauses.append("status = ?")
            args.append(status)
        if search:
            clauses.append("(id LIKE ? OR title LIKE ? OR owner LIKE ?)")
            args.extend([f"%{search}%"] * 3)
        sql = "SELECT * FROM tasks" + (" WHERE " + " AND ".join(clauses) if clauses else "")
        sql += " ORDER BY CASE WHEN status='Blocked' THEN 0 WHEN due_date < ? AND status!='Done' THEN 1 ELSE 2 END, due_date, id LIMIT ?"
        return self.rows(sql, (*args, AS_OF.isoformat(), limit))

    def task(self, task_id):
        row = self.one("SELECT * FROM tasks WHERE id=?", (task_id,))
        if not row:
            return None
        row["predecessors"] = [r["predecessor_id"] for r in self.rows(
            "SELECT predecessor_id FROM dependencies WHERE successor_id=? ORDER BY predecessor_id", (task_id,))]
        row["successors"] = [r["successor_id"] for r in self.rows(
            "SELECT successor_id FROM dependencies WHERE predecessor_id=? ORDER BY successor_id", (task_id,))]
        return row

    def dependency_analysis(self):
        tasks = self.rows("SELECT * FROM tasks ORDER BY id")
        links = self.rows("SELECT * FROM dependencies ORDER BY predecessor_id,successor_id")
        by_id = {t["id"]: t for t in tasks}
        pred = defaultdict(list)
        successors = defaultdict(list)
        for link in links:
            pred[link["successor_id"]].append(link["predecessor_id"])
            successors[link["predecessor_id"]].append(link["successor_id"])
        # Stable topological order is guaranteed by the generator; validate before calculation.
        if any(int(a[2:]) >= int(b[2:]) for a, b in
               ((x["predecessor_id"], x["successor_id"]) for x in links)):
            raise ValueError("Dependency graph contains a backward edge")
        score, parent = {}, {}
        for task in tasks:
            task_id = task["id"]
            remaining = 0 if task["status"] == "Done" else max(1, round(task["duration_days"] * (100 - task["progress"]) / 100))
            best_pred = max(pred[task_id], key=lambda p: score[p], default=None)
            score[task_id] = remaining + (score[best_pred] if best_pred else 0)
            parent[task_id] = best_pred
        end = max(score, key=score.get)
        path = []
        while end:
            path.append(end)
            end = parent[end]
        path.reverse()
        critical_remaining = max(score.values())
        forecast = AS_OF + timedelta(days=critical_remaining)
        blocked_downstream = {}
        for task in tasks:
            if task["status"] != "Blocked":
                continue
            seen, stack = set(), list(successors[task["id"]])
            while stack:
                current = stack.pop()
                if current not in seen:
                    seen.add(current)
                    stack.extend(successors[current])
            blocked_downstream[task["id"]] = len(seen)
        return {
            "edge_count": len(links), "critical_path": path,
            "critical_remaining_days": critical_remaining,
            "forecast_date": forecast.isoformat(),
            "schedule_variance_days": (forecast - RELEASE).days,
            "blocked_downstream": blocked_downstream,
            "nodes": [{"id": t["id"], "team": t["team"], "status": t["status"],
                       "title": t["title"], "due_date": t["due_date"],
                       "critical": t["id"] in path} for t in tasks],
            "edges": [{"source": l["predecessor_id"], "target": l["successor_id"]} for l in links],
        }

    def overview(self):
        tasks = self.rows("SELECT * FROM tasks ORDER BY id")
        raid = self.rows("SELECT * FROM raid ORDER BY id")
        milestones = self.rows("SELECT * FROM milestones ORDER BY due_date")
        dependencies = self.dependency_analysis()
        done = sum(t["status"] == "Done" for t in tasks)
        blocked = sum(t["status"] == "Blocked" for t in tasks)
        overdue = sum(t["due_date"] < AS_OF.isoformat() and t["status"] != "Done" for t in tasks)
        active = [r for r in raid if r["status"] in ACTIVE_RAID]
        critical = [r for r in active if r["severity"] == "Critical"]
        teams = []
        for team in TEAMS:
            ts = [t for t in tasks if t["team"] == team]
            rs = [r for r in active if r["team"] == team]
            teams.append({"name": team, "total": len(ts), "done": sum(t["status"] == "Done" for t in ts),
                          "blocked": sum(t["status"] == "Blocked" for t in ts),
                          "overdue": sum(t["due_date"] < AS_OF.isoformat() and t["status"] != "Done" for t in ts),
                          "active_raid": len(rs), "risk_score": sum(SEVERITY_WEIGHT[r["severity"]] for r in rs)})
        by_raid = {r["id"]: r for r in raid}
        gate_specs = [
            ("Contract signed", "R-003", "Partner authentication v3 signature pending"),
            ("Identity p95 < 350 ms", "R-001", "Observed 418 ms in synthetic sandbox"),
            ("Settlement schema stable", "R-002", "net_amount rename requires adapter patch"),
            ("Audit export complete", "R-004", "Two fields missing in staging sample"),
            ("Fraud threshold approved", "R-010", "Pilot threshold 0.72 signed off"),
            ("Ledger migration approved", "R-014", "48-hour dual-write approved"),
        ]
        gates = []
        for name, source, detail in gate_specs:
            record = by_raid[source]
            status = "passed" if record["status"] in ("Resolved", "Approved", "Accepted") else "watch" if record["status"] == "Mitigating" else "blocked"
            gates.append({"name": name, "status": status, "source": source, "detail": detail})
        # Trend is computed from generated task dates, never hand-entered chart numbers.
        trend = []
        for offset in range(0, 8):
            day = date(2027, 6, 3) + timedelta(days=offset * 7)
            if day > AS_OF:
                break
            planned = sum(t["due_date"] <= day.isoformat() for t in tasks)
            completed = sum(t["status"] == "Done" and t["due_date"] <= day.isoformat() for t in tasks)
            trend.append({"date": day.isoformat(), "planned": planned, "completed": completed})
        return {
            "project": "ProgramPulse AI", "scenario": "Synthetic fintech pilot", "as_of": AS_OF.isoformat(),
            "release_date": RELEASE.isoformat(),
            "metrics": {"tasks": len(tasks), "done": done, "completion_pct": round(done / len(tasks) * 100, 1),
                        "blocked": blocked, "overdue": overdue, "active_raid": len(active),
                        "critical_raid": len(critical), "dependency_edges": dependencies["edge_count"],
                        "forecast_date": dependencies["forecast_date"],
                        "schedule_variance_days": dependencies["schedule_variance_days"],
                        "critical_remaining_days": dependencies["critical_remaining_days"]},
            "teams": teams, "milestones": milestones, "gates": gates, "trend": trend,
            "top_blockers": sorted([r for r in active if r["kind"] == "blocker" or r["severity"] == "Critical"],
                                   key=lambda r: -SEVERITY_WEIGHT[r["severity"]]),
            "critical_path": dependencies["critical_path"],
        }

    def raid(self, kind=None, status=None):
        clauses, args = [], []
        if kind:
            clauses.append("kind=?")
            args.append(kind)
        if status:
            clauses.append("status=?")
            args.append(status)
        return self.rows("SELECT * FROM raid" + (" WHERE " + " AND ".join(clauses) if clauses else "") +
                         " ORDER BY CASE severity WHEN 'Critical' THEN 0 WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, due_date", args)

    def evidence(self, ref):
        if ref.startswith("task:"):
            return self.task(ref[5:])
        if ref.startswith("raid:"):
            return self.one("SELECT * FROM raid WHERE id=?", (ref[5:],))
        if ref.startswith("milestone:"):
            return self.one("SELECT * FROM milestones WHERE id=?", (ref[10:],))
        if ref.startswith("metric:"):
            key = ref[7:]
            value = self.overview()["metrics"].get(key)
            return {"metric": key, "value": value, "as_of": AS_OF.isoformat(), "derivation": "Computed from synthetic SQLite task and RAID records"} if value is not None else None
        return None

    def status_report(self):
        """Grounded extractive synthesis. All numeric claims link to queryable evidence."""
        overview = self.overview()
        m = overview["metrics"]
        dep = self.dependency_analysis()
        ranked = sorted(self.raid(), key=lambda r: (0 if r["status"] == "Escalated" else 1,
                                                  -SEVERITY_WEIGHT[r["severity"]], r["due_date"]))
        actions = []
        for r in ranked:
            if r["status"] not in ACTIVE_RAID:
                continue
            downstream = dep["blocked_downstream"].get(r["task_id"], 0)
            actions.append({
                "priority": "P0" if r["severity"] == "Critical" else "P1" if r["severity"] == "High" else "P2",
                "title": r["title"], "owner_team": r["team"], "due_date": r["due_date"],
                "next_step": r["evidence"], "downstream_tasks": downstream,
                "citations": [f"raid:{r['id']}", f"task:{r['task_id']}"]
            })
        critical_items = [r for r in self.raid() if r["severity"] == "Critical" and r["status"] in ACTIVE_RAID]
        critical_claim = ("Critical active items: " + "; ".join(f"{r['id']} {r['title']}" for r in critical_items) + ".") if critical_items else "No critical RAID items are currently active."
        claims = [
            {"text": f"{m['done']} of {m['tasks']} tasks are complete ({m['completion_pct']}%).",
             "citations": ["metric:done", "metric:tasks", "metric:completion_pct"]},
            {"text": f"{m['blocked']} tasks are blocked and {m['overdue']} are overdue as of {AS_OF.isoformat()}.",
             "citations": ["metric:blocked", "metric:overdue"]},
            {"text": f"The remaining critical path spans {m['critical_remaining_days']} calendar days; the modeled forecast is {m['forecast_date']} ({m['schedule_variance_days']:+d} days vs pilot).",
             "citations": ["metric:critical_remaining_days", "metric:forecast_date", "metric:schedule_variance_days"]},
            {"text": critical_claim, "citations": [f"raid:{r['id']}" for r in critical_items] or ["metric:critical_raid"]},
        ]
        report = {
            "title": "Pilot delivery status", "as_of": AS_OF.isoformat(),
            "health": "Red" if m["critical_raid"] or m["schedule_variance_days"] > 0 else "Amber",
            "method": "Deterministic evidence-grounded synthesis; no LLM or external API is used",
            "claims": claims, "actions": actions[:6],
            "critical_path": dep["critical_path"],
            "source_count": len(set(ref for claim in claims for ref in claim["citations"]) |
                                set(ref for action in actions[:6] for ref in action["citations"])),
        }
        report["markdown"] = "\n".join([
            f"# {report['title']} — {report['as_of']}", f"**Health: {report['health']}**", "",
            "## Executive summary", *[f"- {c['text']} [{', '.join(c['citations'])}]" for c in claims],
            "", "## Escalations and next steps",
            *[f"- **{a['priority']} · {a['owner_team']}** — {a['title']}. {a['next_step']} Due {a['due_date']}. [{', '.join(a['citations'])}]" for a in actions[:6]],
            "", f"*Synthetic scenario. {report['method']}.*",
        ])
        return report

    def tasks_csv(self):
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["id", "title", "team", "owner", "wave", "start_date", "due_date",
                                                       "duration_days", "status", "progress", "priority", "milestone_id", "scenario"])
        writer.writeheader()
        writer.writerows(self.rows("SELECT * FROM tasks ORDER BY id"))
        return output.getvalue()
