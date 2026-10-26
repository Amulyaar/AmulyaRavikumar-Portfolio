#!/usr/bin/env python3
"""Reproduce the bounded RARD recommendation-position audit."""

from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
from pathlib import Path

from analysis_core import summarize_rows

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"
API_URL = "https://dataverse.harvard.edu/api/access/datafile/3026629"
WINDOW_BYTES = 40 * 1024 * 1024
WINDOW_STARTS = (0, 400 * 1024 * 1024, 800 * 1024 * 1024)
ATTRIBUTION = (
    "Beel, Carevic, Schaible, and Neusch (2017), RARD: The Related-Article "
    "Recommendation Dataset, Harvard Dataverse, doi:10.7910/DVN/HA8EAH."
)


def fetch_range(start: int, length: int, timeout: int = 180) -> bytes:
    """Fetch one bounded byte range; fail if the server ignores Range."""
    result = subprocess.run(
        ["curl", "-sS", "-L", "--fail", "--range", f"{start}-{start + length - 1}", API_URL],
        check=True,
        capture_output=True,
        timeout=timeout,
    )
    payload = result.stdout
    if len(payload) > length + 1024 * 1024:
        raise RuntimeError("Dataverse returned more than the requested range; refusing a full-file download")
    return payload


def complete_lines(payload: bytes, first_window: bool):
    """Yield complete TSV lines, dropping partial records at range boundaries."""
    if not payload:
        return [], None
    first_newline = payload.find(b"\n")
    if first_newline < 0:
        return [], None
    if first_window:
        last_newline = payload.rfind(b"\n")
        if last_newline <= first_newline:
            return [], None
        text = payload[: last_newline + 1].decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text), delimiter="\t")
        header = next(reader, None)
        return reader, header

    last_newline = payload.rfind(b"\n")
    if last_newline <= first_newline:
        return [], None
    text = payload[first_newline + 1 : last_newline + 1].decode("utf-8", errors="replace")
    return csv.reader(io.StringIO(text), delimiter="\t"), None


def analyze() -> dict:
    first_rows, header = complete_lines(fetch_range(WINDOW_STARTS[0], WINDOW_BYTES), first_window=True)
    if header is None:
        raise RuntimeError("Dataset header was not found in the first sample window")

    def sampled_rows():
        yield from first_rows
        for start in WINDOW_STARTS[1:]:
            rows, _ = complete_lines(fetch_range(start, WINDOW_BYTES), first_window=False)
            yield from rows

    metrics = summarize_rows(sampled_rows(), header)
    metrics.update(
        {
            "dataset": "RARD: The Related-Article Recommendation Dataset, recommendation_log_0.csv",
            "dataset_doi": "10.7910/DVN/HA8EAH",
            "license": "Creative Commons Attribution 3.0 Unported (CC BY 3.0)",
            "attribution": ATTRIBUTION,
            "method": {
                "sample": "Three non-overlapping 40 MiB byte-range windows at offsets 0, 400 MiB, and 800 MiB from recommendation_log_0.csv.",
                "evaluation": "Descriptive exposure and click-through audit by logged rank; not a causal policy comparison or randomized A/B result.",
                "raw_data_retained": False,
                "rows_skipped": metrics["quality_checks"]["rows_skipped"],
                "algorithm_class_note": (
                    "Algorithm-class values are missing in the sampled rows, so algorithm-arm comparisons are not reported."
                    if metrics["quality_checks"]["all_sampled_algorithm_class_values_missing"]
                    else "Algorithm-class values were present; no strategy-arm causal comparison is performed by this audit."
                ),
                "sample_windows_mib": [0, 400, 800],
                "window_size_mib": 40,
            },
        }
    )
    return metrics


def write_artifacts(metrics: dict) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    with (ARTIFACTS / "rank_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["rank", "exposures", "clicks", "ctr", "click_share", "exposure_share"])
        for rank, values in metrics["by_rank"].items():
            writer.writerow([rank, values["exposures"], values["clicks"], values["ctr"], values["click_share"], values["exposure_share"]])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate committed aggregate artifacts without downloading data")
    args = parser.parse_args()
    if args.check:
        metrics = json.loads((ARTIFACTS / "metrics.json").read_text(encoding="utf-8"))
        assert metrics["sample"]["recommendation_rows"] == 1_023_019, "unexpected impression count"
        assert metrics["sample"]["recommendation_sets"] == 102_311, "unexpected slate count"
        assert metrics["sample"]["clicked_recommendations"] == 1_642, "unexpected click count"
        rank_exposures = sum(item["exposures"] for item in metrics["by_rank"].values())
        rank_clicks = sum(item["clicks"] for item in metrics["by_rank"].values())
        assert rank_exposures == metrics["sample"]["recommendation_rows"], "rank exposures do not reconcile to total rows"
        assert rank_clicks == metrics["sample"]["clicked_recommendations"], "rank clicks do not reconcile to total clicks"
        assert abs(metrics["position_comparison"]["rank_1_ctr_ratio_vs_ranks_2_to_10"] - 2.627) < 0.001
        print("Committed aggregate artifacts pass the known-result checks.")
        return
    metrics = analyze()
    write_artifacts(metrics)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
