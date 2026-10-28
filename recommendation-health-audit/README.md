# Recommendation Health Audit

An end-to-end product analytics case study on **how recommendation position relates to clicks**. It analyzes a bounded sample of public RARD recommendation logs, produces aggregate artifacts and a portfolio page, then turns the observational pattern into a proposed randomized rank-swap experiment.

## Finding

The analyzed sample contains **1,023,019 recommendation impressions across 102,311 slates**. Rank 1's observed CTR was **0.3626%**, compared with **0.1380%** for ranks 2–10, a **2.63× descriptive ratio**. Rank 1 represented about **10.0% of sampled impressions and 22.6% of clicks**.

This is an observational diagnostic, not a causal estimate, model win, or A/B-test result. The sample is three deterministic byte ranges from one scholarly-article recommendation log shard;

## What the project demonstrates

- **Product framing:** distinguish item relevance from position and exposure before interpreting a CTR change.
- **Data analysis:** parse a large tab-separated log in bounded ranges; validate required columns and ranks; aggregate impressions and clicks by rank and slate.
- **Measurement judgment:** preserve the descriptive/causal boundary, surface missing strategy metadata, and retain no raw rows in the repository.
- **Experiment design:** propose a stable user-level randomized rank swap with a fixed candidate set, a primary moved-item CTR metric, ecosystem guardrails, and planning-only power scenarios.
- **Communication:** provide an executive case study and a responsive static portfolio page.

## Reproduce

Requirements: Python 3 and `curl`. The analysis uses only the Python standard library. From this directory:

```bash
python3 -m unittest discover -s tests -v
python3 analyze.py --check
python3 experiment_design.py
python3 analyze.py
```

`analyze.py` downloads three 40 MiB byte ranges at offsets 0, 400 MiB, and 800 MiB from the public source file. It keeps the ranges in memory while parsing and writes **aggregate-only** `artifacts/metrics.json` and `artifacts/rank_metrics.csv`; it does not store source rows. The range window selection is fixed for reproducibility and must not be described as random sampling.

`experiment_design.py` reads the committed aggregate metrics and writes `artifacts/experiment_plan.json`. Its sample-size scenarios use the observed ranks 2–10 CTR only as an illustrative baseline. They are independent-impression approximations, not an approved launch plan or power guarantee; the final design requires a live baseline and user-cluster-aware power analysis.

## Project map

```text
analysis_core.py              Pure aggregation logic
analyze.py                    Bounded source download and artifact generation
experiment_design.py          Experiment proposal and planning scenarios
tests/                        Unit tests for aggregation and planning logic
artifacts/metrics.json        Aggregate audit results and method metadata
artifacts/rank_metrics.csv   CTR/exposure/click counts by rank
artifacts/experiment_plan.json Proposed experiment and planning-only scenarios
case_study.md                 Full product case study
index.html                    Portfolio-ready static page (GitHub Pages entry point)
```

To publish the portfolio page later, place this folder at the root of a GitHub repository and enable GitHub Pages from the repository's default branch. The `index.html` page uses relative links to the aggregate artifacts. Do not add the raw RARD source file to the repository.

## Experiment proposal (not run)

Randomize eligible users to original ranking (control) or a rank-swap treatment that swaps rank 1 with one uniformly selected item from ranks 2–10, keeping the candidate set fixed. Measure click-through on the preselected moved item within a prespecified attribution window. Analyze intention-to-treat with user-clustered uncertainty.

Pair the primary metric with useful engagement/read depth and, where product instrumentation supports them, hides/reports or quick returns, exposure concentration, and category/creator/format coverage. Set guardrail thresholds and stopping rules before launch. The RARD sample itself lacks user, creator, content-quality, and negative-feedback labels; these outcomes are proposed for a future instrumented product test, not claimed as measured here.

## Dataset attribution

Beel, J., Carevic, Z., Schaible, J., and Neusch, G. (2017). *RARD: The Related-Article Recommendation Dataset*. Harvard Dataverse. [Dataset DOI](https://doi.org/10.7910/DVN/HA8EAH). Dataset license: Creative Commons Attribution 3.0 Unported (CC BY 3.0). The repository contains derived aggregate counts only, not source rows.


Audited 1.02M recommendation impressions across 102K slates in the public RARD dataset; observed 0.36% CTR at rank 1 versus 0.14% at ranks 2–10 (2.63× descriptive ratio) and proposed a randomized rank-swap test with engagement and ecosystem-health guardrails.
