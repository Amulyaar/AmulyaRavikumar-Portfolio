"""Reproducible local timing benchmark for the synthetic delivery simulator."""
import argparse
import csv
import json
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from engine import Store  # noqa: E402


def percentile(values, p):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int((len(ordered) - 1) * p + .999)))]


def measure(fn, iterations):
    samples = []
    result = None
    for _ in range(iterations):
        start = time.perf_counter()
        result = fn()
        samples.append((time.perf_counter() - start) * 1000)
    return {"iterations": iterations, "mean_ms": round(statistics.mean(samples), 3),
            "median_ms": round(statistics.median(samples), 3), "p95_ms": round(percentile(samples, .95), 3),
            "min_ms": round(min(samples), 3), "max_ms": round(max(samples), 3)}, result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument("--json", default=str(ROOT / "benchmarks" / "results.json"))
    parser.add_argument("--csv", default=str(ROOT / "benchmarks" / "results.csv"))
    args = parser.parse_args()
    if args.iterations < 2:
        parser.error("use at least two iterations")
    with tempfile.TemporaryDirectory() as temp:
        store = Store(Path(temp) / "benchmark.db")
        measurements = {}
        measurements["overview"], overview = measure(store.overview, args.iterations)
        measurements["dependency_analysis"], graph = measure(store.dependency_analysis, args.iterations)
        measurements["status_report"], report = measure(store.status_report, args.iterations)
        measurements["task_search"], search_result = measure(lambda: store.tasks(search="settlement", limit=50), args.iterations)
        measurements["csv_export"], csv_result = measure(store.tasks_csv, args.iterations)
        output = {
            "project": "ProgramPulse AI", "scenario": "Synthetic fintech pilot",
            "measurement": "Local wall-clock execution time; no network calls",
            "environment": {"python": platform.python_version(), "platform": platform.platform(),
                            "processor": platform.processor() or "not reported"},
            "dataset": {"tasks": overview["metrics"]["tasks"], "dependencies": graph["edge_count"],
                        "raid_items": len(store.raid()), "report_citations": report["source_count"],
                        "search_rows_returned": len(search_result), "csv_bytes": len(csv_result.encode("utf-8"))},
            "iterations": args.iterations, "results": measurements,
            "notes": ["Results describe this local machine and Python runtime.",
                      "Benchmarks time the engine functions, not browser rendering or HTTP transport.",
                      "The database is newly seeded from the fixed 2027 synthetic scenario for every run."],
        }
    json_path, csv_path = Path(args.json), Path(args.csv)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(output, indent=2) + "\n")
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["operation", "iterations", "mean_ms", "median_ms", "p95_ms", "min_ms", "max_ms"])
        writer.writeheader()
        for operation, values in measurements.items():
            writer.writerow({"operation": operation, **values})
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
