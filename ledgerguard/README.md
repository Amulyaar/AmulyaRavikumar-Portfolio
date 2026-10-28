# LedgerGuard | FinTech Release Readiness & Quality Engineering

A runnable release-quality command center for a simulated supplier-payments platform. It generates a fixed-seed batch of 1,000 synthetic invoices, injects controlled failure scenarios, applies deterministic financial and integration checks, tracks finding triage, and calculates a risk-based release decision.

> **Synthetic project.** All suppliers, invoices, findings, dates, performance observations, and benchmark outcomes are generated locally. This is not a payment product and does not connect to a bank, processor, or real customer data. The evidence-grounded status brief is deliberately deterministic and uses no external model.

## What it demonstrates

- Invoice, beneficiary, purchase-order, approval, payment-reference, gateway, ledger, and audit-document controls.
- A 1,000-invoice / 25 seeded high-severity fault dataset, including one opaque defect that should remain undetected. Recall is calculated against embedded synthetic labels, not assumed.
- Severity-weighted risk, at-risk payment exposure, reconciliation and latency metrics, and explicit GO / NO-GO gates.
- Traceable report claims with links to metric, finding, invoice, and benchmark evidence.
- Finding search, severity/status filters, persistent triage, invoice detail API, and CSV export.
- SQLite for the quick local path and SQLAlchemy support for PostgreSQL.
- 100+ rule-matrix/regression test cases, branch coverage enforcement in CI, and a repeatable benchmark that exports JSON and CSV results.

## Run locally

Requires Python 3.11 or newer. For the easiest setup, use SQLite (default):

```bash
cd outputs/ledgerguard
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
python -m pip install -e '.[test]'
uvicorn ledgerguard.api:app --reload
```

Open <http://127.0.0.1:8000>. The first request creates the SQLite snapshot at `ledgerguard.db`. The dataset uses a stable random seed, so the same controls produce repeatable inputs.

### PostgreSQL option

```bash
docker compose up -d postgres
export DATABASE_URL='postgresql+psycopg://ledgerguard:ledgerguard_local@localhost:5432/ledgerguard'
uvicorn ledgerguard.api:app --reload
```

The application creates its small snapshot table on startup. For production use, add migrations, authentication, access controls, audit retention, connection-secret management, and database backups before exposing it beyond a local demo.

## Verify controls and coverage

```bash
pytest --cov=ledgerguard.engine --cov-branch --cov-report=term-missing --cov-fail-under=85
```

The test suite is designed to exceed 100 checks and CI blocks a merge if `ledgerguard.engine` falls below 85% branch-aware line coverage. The threshold is an automated quality gate; do not describe it as measured coverage until a successful CI run reports the actual percentage.

### Local verification captured for this build

- `unittest`: 136 tests discovered; 128 passed and 8 API integration tests were skipped because the local runtime does not have the FastAPI/SQLAlchemy dependencies installed. CI installs them and runs those tests.
- Python's standard-library `trace` summary reports 100% executed-line coverage for `ledgerguard.engine` (136 lines in its trace report). This is line execution coverage, not branch-aware `pytest-cov`; the CI threshold above remains the branch-coverage check.
- Fixed-seed benchmark: 30 evaluations of 1,000 invoices; median engine evaluation 0.472 ms, p95 0.497 ms on Python 3.12.14 / macOS 27.0.1 arm64. This measures in-process rule evaluation only, not API, database, network, or payment-provider latency.
- Scenario results: 24/25 seeded high-severity defects detected (96.00% recall), 98.50% of all invoices posted and reconciled, API fixture p95 637 ms, and five blocked release gates. The correct result is NO-GO.

## Reproduce benchmark outputs

```bash
python benchmarks/run_benchmark.py
```

This runs the fixed-seed 1,000-invoice evaluation 30 times by default and writes `benchmarks/results.json` and `benchmarks/results.csv`. Set `LEDGERGUARD_ITERATIONS` to change the iteration count. Reported wall-clock timings are specific to the machine and include neither API/network latency nor database latency. The benchmark script records its Python version and platform alongside measured values.

## API quick reference

- `GET /api/health`, `/api/overview`, `/api/report`
- `GET /api/findings?severity=high&status=Open&search=INV-2027`
- `PATCH /api/findings/{finding_id}/status` with `{"status":"Investigating"}` (also `Open`, `Resolved`, `Accepted`)
- `GET /api/invoices`, `/api/invoices/{invoice_id}`
- `GET /api/evidence/{reference}` for `metric:…`, `benchmark:…`, `finding:…`, or `invoice:…`
- `GET /api/export/findings.csv`

## Scenario and decision policy

The fixture generator seeds 24 observable high-severity defects and one opaque fraud hold with no validator-visible signal. It also injects latency, missing audit documents, and unposted ledger entries. The evaluation measures seeded-defect recall, then separately applies release gates: no open critical controls, no open duplicate references, at least 99.5% ledger match, API p95 no greater than 450 ms, complete invoice document hashes, and at least 96% high-severity recall. Open findings can be triaged in the dashboard; the decision recalculates against their persisted status. “Accepted” closes an item from the open risk count in this demo; a real financial process would require explicit approval and an audit trail.

The generator uses a documented `$1.00` PO variance tolerance and a two-approver rule for invoices of `$10,000` or more. These are demonstration assumptions, not externally sourced compliance requirements.

## Project structure

```text
ledgerguard/       validation engine, deterministic dataset, API, SQLAlchemy snapshot store
tests/             unit and rule-matrix regression suite
web/               responsive dashboard (plain HTML/CSS/JS)
benchmarks/        reproducible runner and measured JSON/CSV outputs
.github/workflows/ PostgreSQL-backed CI and coverage gate
```

## Resume wording (only after verifying CI)

A defensible draft, with numbers tied to reproducible artifacts:

- Built LedgerGuard, a FastAPI financial release-readiness simulator that evaluates 1,000 fixed-seed synthetic invoices across payment, approval, integration, audit, and ledger controls; implemented risk-based go/no-go gates, persistent issue triage, evidence-linked reporting, and CSV exports.
- Added 136 automated checks (128 passed in the local stdlib run; eight FastAPI integration checks are enabled in CI) and recorded 100% executed-line coverage of the rule engine with Python `trace`; configured PostgreSQL-backed GitHub Actions to require at least 85% branch-aware coverage.
- Benchmarked 30 runs over 1,000 synthetic invoices at a 0.472 ms median rule-evaluation time on Python 3.12.14 / macOS 27.0.1 arm64; the measurement excludes API/database/network latency.
- Measured detection of **24/25 (96%)** seeded high-severity defects, with the intentionally unobservable fraud-hold case documented as a known limitation.

Replace bracketed values only with successful CI and benchmark output. Do not claim actual customer savings, production payment protection, or performance outside the recorded local run.
