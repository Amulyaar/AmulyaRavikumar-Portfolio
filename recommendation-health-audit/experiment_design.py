"""Planning-only sample-size scenarios for a proposed rank-swap experiment.

These estimates are not experiment results or launch recommendations. They use
an observational RARD CTR only as a planning anchor and omit user-clustering
inflation, so they are lower-bound approximations.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
METRICS_PATH = ROOT / "artifacts" / "metrics.json"
OUTPUT_PATH = ROOT / "artifacts" / "experiment_plan.json"


def two_proportion_sample_size_per_arm(p_control: float, relative_mde: float, alpha: float = 0.05, power: float = 0.80) -> int:
    """Approximate independent observations per arm for a two-sided test."""
    if not 0 < p_control < 1:
        raise ValueError("p_control must be between 0 and 1")
    if relative_mde <= 0 or p_control * (1 + relative_mde) >= 1:
        raise ValueError("relative_mde must be positive and produce a valid treatment rate")
    if not 0 < alpha < 1 or not 0 < power < 1:
        raise ValueError("alpha and power must be between 0 and 1")

    # Standard normal quantiles for the conventional 95%/80% planning case.
    # General values use a compact inverse-normal approximation.
    z_alpha = 1.959963984540054 if alpha == 0.05 else _inverse_normal(1 - alpha / 2)
    z_power = 0.8416212335729143 if power == 0.80 else _inverse_normal(power)
    p_treatment = p_control * (1 + relative_mde)
    pooled = (p_control + p_treatment) / 2
    numerator = z_alpha * math.sqrt(2 * pooled * (1 - pooled))
    numerator += z_power * math.sqrt(p_control * (1 - p_control) + p_treatment * (1 - p_treatment))
    return math.ceil(numerator**2 / (p_treatment - p_control) ** 2)


def _inverse_normal(probability: float) -> float:
    """Acklam's inverse-normal approximation; sufficient for planning output."""
    if not 0 < probability < 1:
        raise ValueError("probability must be between 0 and 1")
    a = (-39.6968302866538, 220.946098424521, -275.928510446969, 138.357751867269, -30.6647980661472, 2.50662827745924)
    b = (-54.4760987982241, 161.585836858041, -155.698979859887, 66.8013118877197, -13.2806815528857)
    c = (-0.00778489400243029, -0.322396458041136, -2.40075827716184, -2.54973253934373, 4.37466414146497, 2.93816398269878)
    d = (0.00778469570904146, 0.32246712907004, 2.445134137143, 3.75440866190742)
    low = 0.02425
    high = 1 - low
    if probability < low:
        q = math.sqrt(-2 * math.log(probability))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if probability > high:
        q = math.sqrt(-2 * math.log(1 - probability))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = probability - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def build_plan(metrics: dict) -> dict:
    baseline = metrics["position_comparison"]["ranks_2_to_10_ctr"]
    scenarios = []
    for relative_mde in (0.05, 0.10, 0.20):
        scenarios.append(
            {
                "relative_mde": relative_mde,
                "assumed_control_ctr": baseline,
                "assumed_treatment_ctr": baseline * (1 + relative_mde),
                "approx_independent_impressions_per_arm": two_proportion_sample_size_per_arm(baseline, relative_mde),
            }
        )
    return {
        "status": "planning scenario only; no randomized experiment was run",
        "design": {
            "question": "Does moving a recommendation into rank 1 change its click probability, holding the candidate item constant?",
            "eligible_population": "Recommendation slates with a stable candidate set and no policy or safety exclusions.",
            "randomization_unit": "User, to keep assignment stable across repeated slates and reduce cross-arm contamination.",
            "control": "Original ranking.",
            "treatment": "Swap rank 1 with one uniformly selected item from ranks 2–10; keep the candidate set unchanged.",
            "primary_metric": "Click-through rate of the preselected moved item within a prespecified attribution window.",
            "guardrails": [
                "Slate-level useful engagement (for example, article opens followed by meaningful read depth).",
                "Hide/report or quick-return rate, where available.",
                "Exposure concentration and category/creator/format coverage, where those labels exist.",
            ],
            "analysis": "Intention-to-treat comparison with user-clustered uncertainty; report absolute and relative effects with confidence intervals.",
        },
        "power_scenarios": {
            "alpha_two_sided": 0.05,
            "power": 0.80,
            "baseline_anchor": "Observed ranks 2–10 CTR from the bounded observational sample; used only to illustrate planning scale.",
            "warning": "Per-arm counts are independent-impression approximations. Final design must account for user clustering, eligibility, attrition, multiple guardrails, and the actual live baseline.",
            "scenarios": scenarios,
        },
    }


def main() -> None:
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    plan = build_plan(metrics)
    OUTPUT_PATH.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
