# ProgramPulse AI

**A local fintech program delivery command center for a fictional Summer 2027 pilot.** It brings five teams, 500 simulated tasks, dependency analysis, a RAID log, release gates, and traceable status reporting into one React dashboard.

> **Synthetic project data.** Every person, work item, risk, milestone, and event in this repository is fictional. The snapshot date is July 15, 2027. This is a portfolio simulation, not an Intuit system or a production forecast.

## What it does

- **Program overview:** completion, blocked and overdue work, team rollups, delivery pace, milestones, and release gates.
- **Dependency analysis:** 705 generated handoffs form a directed acyclic graph. The engine calculates the longest remaining dependency chain, a simple forecast date, and the downstream blast radius of blocked work.
- **RAID management:** filter 15 synthetic risks, assumptions, issues, and decisions; escalate active items and see the status brief refresh.
- **Evidence-linked status brief:** every numeric claim and recommended action has clickable references into task, RAID, milestone, or computed metric records. Export the report as JSON and the full task register as CSV.
- **Reproducible results:** deterministic seed data, unit tests, and a local benchmark runner that writes measured JSON and CSV results.

## Run locally

Requirements: Python 3.10 or newer, Node.js 18 or newer, npm, and network access for the first dependency install. SQLite ships with Python.

In one terminal, from this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/simulate.py
cd backend
uvicorn main:app --reload
```

The API is at `http://127.0.0.1:8000`; interactive API docs are at `http://127.0.0.1:8000/docs`.

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Vite forwards `/api` requests to the local FastAPI service.

The first seed creates `backend/programpulse.db`; subsequent starts keep the current state. To reset every record to the reproducible baseline, stop the API and run `python backend/simulate.py --force` from the project root.

To store the database elsewhere, set `PROGRAMPULSE_DB` before starting Uvicorn. The database file is excluded from version control.

## Tests and benchmarks

Run the engine tests with:

```bash
python -m unittest discover -s backend -v
```

Run 30 benchmark iterations (or pass `--iterations N`):

```bash
python benchmarks/run_benchmarks.py --iterations 30
```

The checked-in `benchmarks/results.json` and `benchmarks/results.csv` are the recorded output from this run on macOS 27.0.1 arm64 with Python 3.12.14. The benchmark times SQLite-backed engine functions, excluding HTTP transport and browser rendering. It uses a fresh temporary SQLite database seeded from the same fixed scenario each time.

| Operation | Median | p95 |
| --- | ---: | ---: |
| Overview metrics | 3.764 ms | 4.436 ms |
| Dependency analysis | 1.567 ms | 1.711 ms |
| Evidence-grounded status brief | 5.135 ms | 5.531 ms |
| Task search | 0.160 ms | 0.177 ms |
| CSV export | 1.401 ms | 1.523 ms |

These are local measurements, not service-level guarantees. Re-run the benchmark to measure on another machine.

## Status report method

The project currently uses deterministic, evidence-grounded synthesis rather than a hosted language model. It calculates metrics from the SQLite snapshot and selects open RAID items by severity and status. Citation references resolve through `GET /api/evidence/{reference}`. This makes the local project self-contained and ensures the report cannot introduce untraceable facts. It is not a general-purpose generative AI model.

## API overview

| Endpoint | Purpose |
| --- | --- |
| `GET /api/overview` | Program KPIs, teams, milestones, gates, and trend series |
| `GET /api/tasks?team=Payments&search=ledger` | Filter the task register |
| `GET /api/tasks/{task_id}` | Task detail with predecessor and successor IDs |
| `GET /api/graph?scope=critical` | Critical path trace, graph metrics, and blocked downstream counts |
| `GET /api/raid` | RAID records |
| `PATCH /api/raid/{item_id}` | Change a RAID status to Open, Escalated, Mitigating, or Resolved |
| `GET /api/reports/status` | Grounded report with claims, action list, citations, and Markdown |
| `GET /api/evidence/{reference}` | Resolve `task:`, `raid:`, `milestone:`, and `metric:` references |
| `GET /api/export/tasks.csv` | Export all 500 tasks |
| `GET /api/export/status.json` | Export the current report |

## Modeling limits

The schedule forecast adds the longest remaining task-duration chain to the snapshot date. It uses calendar days and does not account for working calendars, resource capacity, uncertainty, or shared-resource contention. Team completion is a snapshot metric, not a validated delivery commitment. The sample uses invented people and deliberately seeded integration failures to make the dashboard demonstrable.

## Portfolio resume bullets

Use these only as claims about this completed portfolio simulation; preserve the synthetic-data context when discussing it:

- Built a React and FastAPI fintech program command center modeling 5 cross-functional teams, 500 work items, and 705 task dependencies; implemented critical-path forecasting, release gates, RAID escalation, and CSV/JSON exports.
- Created evidence-linked status reporting that ties each claim to task, milestone, RAID, or computed metric records; measured a 5.531 ms p95 report-generation time over 30 local runs on a 500-task SQLite dataset.

The measurements describe local engine execution, not the AI quality or browser response time.
