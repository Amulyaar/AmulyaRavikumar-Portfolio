# Recommendation Health Audit

**Product analytics case study by Amulya Ravikumar**  
**Status:** Completed offline descriptive audit; online experiment proposed, not run  
**Dataset:** Public RARD scholarly-article recommendation logs

## Executive readout

Across **1,023,019 recommendation impressions in 102,311 slates**, the observed CTR was **0.3626% at rank 1** and **0.1380% across ranks 2–10**. The ratio was **2.63×** using the unrounded rates. Rank 1 accounted for about **10.0% of sampled impressions and 22.6% of logged clicks**.

The product conclusion is not that rank 1 caused more clicks. The audit cannot separate position from item quality or slate context. It flags a measurement risk: a ranking change can appear better on raw CTR if its items receive more prominent exposure. I proposed a randomized rank-swap test to measure position's effect while holding the candidate set constant.

## Product question

When a recommendation strategy reports more clicks, did it select more useful content, or did it place content where people were more likely to notice it? Before making a rollout decision, a PM needs a measurement plan that distinguishes recommendation quality from exposure and protects broader user and ecosystem outcomes.

## Data and method

The audit uses the public **RARD: The Related-Article Recommendation Dataset**, a log of related scholarly-article recommendations and clicks. It downloads three 40 MiB byte ranges at offsets 0, 400 MiB, and 800 MiB from `recommendation_log_0.csv` in Harvard Dataverse. Partial boundary records are discarded. The parser validates required fields and ranks, then aggregates exposures and clicks by rank and slate. Only aggregate outputs are saved.

The sample contains 1,023,019 rows, 102,311 slates, and 1,642 logged clicks. `algorithm-class` is missing in every sampled row, so this project does not compare recommender algorithm arms. The bounded byte windows are reproducible, but they are not a random sample of the full dataset; the sampled dates are concentrated in a few periods.

| Measure | Observed value |
| --- | ---: |
| Recommendation impressions | 1,023,019 |
| Recommendation slates | 102,311 |
| Logged clicks | 1,642 |
| Overall observed CTR | 0.1605% |
| Rank 1 CTR | 0.3626% |
| Ranks 2–10 CTR | 0.1380% |
| Rank 1 / ranks 2–10 CTR ratio | 2.63× |
| Rank 1 impression share / click share | 10.0% / 22.6% |

## Interpretation and PM decision

Rank 1's higher observed CTR is consistent with a position effect, but the data cannot establish that explanation. It may also reflect relevance, audience, or slate composition. Clicks are a weak value proxy, and the source does not contain article-quality, creator, content-mix, or negative-feedback labels.

For product decisions, raw CTR should be read with exposure context and additional value measures. For a short-form content product, an equivalent monitoring plan could pair engagement with completion, hides/reports, repeat exposure, and creator/category/format exposure distribution. Those are proposed measures; this RARD dataset cannot calculate them.

## Proposed randomized rank-swap test

**Hypothesis:** For the same candidate item and slate context, placing a randomly selected lower-ranked recommendation at rank 1 changes its click probability.

- **Eligible population:** Slates with a stable candidate set and no policy or safety exclusions.
- **Randomization:** Assign users consistently to control or treatment to avoid users crossing between arms across repeated slates.
- **Control:** Keep the original ranking.
- **Treatment:** Swap rank 1 with one uniformly selected item from ranks 2–10; keep the candidate set unchanged.
- **Primary metric:** CTR of the preselected moved item within a prespecified attribution window.
- **Guardrails:** Useful engagement/read depth; hides/reports or quick returns where available; exposure concentration and category/creator/format coverage where labels exist.
- **Analysis:** Intention-to-treat with user-clustered uncertainty. Report absolute and relative effects with confidence intervals, and define guardrail thresholds and stopping rules before launch.

The planning script illustrates independent-impression sample sizes for 5%, 10%, and 20% relative MDEs from the observed ranks 2–10 CTR: approximately **4.66M**, **1.19M**, and **312K impressions per arm**, respectively. These are only scale examples: they use an observational baseline and do not account for repeated exposures per user, eligibility, attrition, or guardrail multiplicity. A real test needs a live baseline and user-cluster-aware power calculation.

## Reproduction and files

```bash
python3 -m unittest discover -s tests -v
python3 analyze.py --check
python3 experiment_design.py
python3 analyze.py
```

The first three commands run offline. The final command fetches the bounded source ranges and regenerates `artifacts/metrics.json` and `artifacts/rank_metrics.csv`. The planning script writes `artifacts/experiment_plan.json`. The project uses Python's standard library and `curl` only; raw dataset rows are not included.

## Attribution and limitations

Beel, J., Carevic, Z., Schaible, J., and Neusch, G. (2017). *RARD: The Related-Article Recommendation Dataset*. Harvard Dataverse, [DOI: 10.7910/DVN/HA8EAH](https://doi.org/10.7910/DVN/HA8EAH). Dataset license: CC BY 3.0.

This is a deterministic byte-range sample of one scholarly recommendation log shard, not a random sample or a TikTok dataset. Position and item quality are confounded. The project does not establish causal lift, compare strategy arms, measure creator or content health, train a ranking model, or run an online experiment.
