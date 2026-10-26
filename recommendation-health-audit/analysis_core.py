"""Pure aggregation functions for the RARD recommendation-position audit."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable, Sequence


def summarize_rows(rows: Iterable[Sequence[str]], header: Sequence[str]) -> dict:
    """Aggregate parsed TSV rows into descriptive position metrics.

    A row is one logged recommendation impression. `clicked` is treated as a
    click when it contains a non-null value, matching the source log schema.
    This function does not estimate causal effects.
    """
    idx = {name: position for position, name in enumerate(header)}
    required = {"rank_in_set", "recommendation_set_id", "clicked", "set_size", "algorithm-class", "request_received"}
    missing = required.difference(idx)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    by_rank = defaultdict(lambda: [0, 0])
    clicks_by_slate = Counter()
    slate_rows = Counter()
    set_sizes = Counter()
    algorithms = Counter()
    dates = Counter()
    rows_skipped = 0
    total = clicks = 0

    for row in rows:
        try:
            rank = int(row[idx["rank_in_set"]])
            slate_id = row[idx["recommendation_set_id"]]
            set_size = int(row[idx["set_size"]])
            clicked = row[idx["clicked"]] not in ("NULL", "", "null")
            received = row[idx["request_received"]]
            algorithm = row[idx["algorithm-class"]]
            if not slate_id or not 1 <= rank <= 100 or set_size < rank:
                raise ValueError("Invalid slate, rank, or slate size")
        except (IndexError, ValueError):
            rows_skipped += 1
            continue

        by_rank[rank][0] += 1
        by_rank[rank][1] += int(clicked)
        clicks_by_slate[slate_id] += int(clicked)
        slate_rows[slate_id] += 1
        set_sizes[set_size] += 1
        algorithms[algorithm] += 1
        dates[received[:10]] += 1
        total += 1
        clicks += int(clicked)

    rank1_exp, rank1_clicks = by_rank[1]
    tail_exp = sum(n for rank, (n, _) in by_rank.items() if 2 <= rank <= 10)
    tail_clicks = sum(n for rank, (_, n) in by_rank.items() if 2 <= rank <= 10)
    rank1_ctr = rank1_clicks / rank1_exp if rank1_exp else 0.0
    tail_ctr = tail_clicks / tail_exp if tail_exp else 0.0

    return {
        "sample": {
            "recommendation_rows": total,
            "recommendation_sets": len(slate_rows),
            "clicked_recommendations": clicks,
            "overall_ctr": round(clicks / total, 7) if total else 0.0,
            "date_counts": dict(sorted(dates.items())),
            "set_size_row_counts": {str(k): v for k, v in sorted(set_sizes.items())},
            "sets_with_multiple_logged_clicks": sum(v > 1 for v in clicks_by_slate.values()),
        },
        "position_comparison": {
            "rank_1_exposures": rank1_exp,
            "rank_1_clicks": rank1_clicks,
            "rank_1_ctr": round(rank1_ctr, 7),
            "ranks_2_to_10_exposures": tail_exp,
            "ranks_2_to_10_clicks": tail_clicks,
            "ranks_2_to_10_ctr": round(tail_ctr, 7),
            "rank_1_ctr_ratio_vs_ranks_2_to_10": round(rank1_ctr / tail_ctr, 3) if tail_ctr else None,
            "rank_1_share_of_clicks": round(rank1_clicks / clicks, 6) if clicks else 0.0,
            "rank_1_share_of_exposures": round(rank1_exp / total, 6) if total else 0.0,
        },
        "algorithm_class_counts": dict(algorithms),
        "by_rank": {
            str(rank): {
                "exposures": exposures,
                "clicks": rank_clicks,
                "ctr": round(rank_clicks / exposures, 7) if exposures else 0.0,
                "click_share": round(rank_clicks / clicks, 6) if clicks else 0.0,
                "exposure_share": round(exposures / total, 6) if total else 0.0,
            }
            for rank, (exposures, rank_clicks) in sorted(by_rank.items())
        },
        "quality_checks": {
            "rows_skipped": rows_skipped,
            "all_sampled_algorithm_class_values_missing": bool(algorithms) and set(algorithms) <= {"NULL", "", "null"},
            "slates_with_multiple_logged_clicks": sum(v > 1 for v in clicks_by_slate.values()),
        },
    }


def resume_metrics(summary: dict) -> dict:
    """Return the exact resume-facing values, formatted from full precision."""
    sample = summary["sample"]
    position = summary["position_comparison"]
    return {
        "impressions": sample["recommendation_rows"],
        "slates": sample["recommendation_sets"],
        "rank_1_ctr_percent": position["rank_1_ctr"] * 100,
        "ranks_2_to_10_ctr_percent": position["ranks_2_to_10_ctr"] * 100,
        "descriptive_ratio": position["rank_1_ctr_ratio_vs_ranks_2_to_10"],
    }
