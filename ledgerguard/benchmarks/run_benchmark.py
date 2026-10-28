"""Reproducible stdlib benchmark for the 1,000-invoice scenario."""
from __future__ import annotations
import csv, json, os, platform, statistics, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ledgerguard.data import generate_invoices
from ledgerguard.engine import build_report, evaluate_invoices

ROOT = Path(__file__).resolve().parent
N = int(os.getenv("LEDGERGUARD_ITERATIONS", "30"))

def main():
    invoices = generate_invoices()
    evaluation_ms, report_ms = [], []
    assessment = None
    for _ in range(N):
        start = time.perf_counter()
        assessment = evaluate_invoices(invoices)
        evaluation_ms.append((time.perf_counter() - start) * 1000)
        start = time.perf_counter()
        build_report(assessment)
        report_ms.append((time.perf_counter() - start) * 1000)
    result = {
        "benchmark": "LedgerGuard fixed-seed synthetic invoice release simulation",
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "cpu_count": os.cpu_count()},
        "dataset": {"invoices": len(invoices), "iterations": N, "seed": 2027},
        "evaluation_ms": {"median": round(statistics.median(evaluation_ms), 3), "p95": round(sorted(evaluation_ms)[int(.95 * (N - 1))], 3), "min": round(min(evaluation_ms), 3), "max": round(max(evaluation_ms), 3)},
        "report_build_ms": {"median": round(statistics.median(report_ms), 3), "p95": round(sorted(report_ms)[int(.95 * (N - 1))], 3)},
        "quality": {"seeded_high_severity": assessment["seeded_high_severity"], "true_positive_high_severity": assessment["true_positive_high_severity"], "recall_pct": assessment["high_severity_recall_pct"], "finding_count": assessment["finding_count"], "reconciliation_pct": assessment["reconciliation_pct"], "p95_api_latency_ms": assessment["p95_latency_ms"], "blocked_gates": assessment["blocked_gates"], "decision": assessment["release_decision"]},
        "note": "Wall-clock results vary by machine; generated locally by run_benchmark.py. No API/network latency is included."
    }
    (ROOT / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    with (ROOT / "results.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["metric", "value"])
        for key, value in result["evaluation_ms"].items(): w.writerow([f"evaluation_{key}_ms", value])
        for key, value in result["report_build_ms"].items(): w.writerow([f"report_{key}_ms", value])
        for key, value in result["quality"].items(): w.writerow([f"quality_{key}", value])
    print(json.dumps(result, indent=2))

if __name__ == "__main__": main()
