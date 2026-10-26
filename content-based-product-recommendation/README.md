# Discovery Mix Lab

An interactive content-based product recommendation demo and PM case study by Amulya Ravikumar. It is designed to show how relevance, freshness, and category variety can change a discovery feed.

## Try it

Open `index.html` in a modern browser, or serve this folder as a static site. The playground runs fully in the browser and needs no package installation or network calls. The catalog is generated deterministically from a small set of product categories and descriptive attributes.

## What the demo does

- Generates a reproducible catalog of 10,000 synthetic items.
- Lets a visitor select interests and tune relevance, freshness, and exploration weights.
- Compares three illustrative ranking strategies: taste match, fresh picks, and open horizons.
- Shows why an item appeared and reports calculated demo proxies for match, category coverage, and freshness.
- Lets a visitor save or hide items for the current page session.
- Keeps the ranking core independent from the presentation layer so its behavior can be tested.

## Project result and evidence boundary

The case study reports the result supplied for the original personal project: three recommendation approaches were A/B-tested on engagement metrics, and the best variant lifted CTR by approximately 10% over baseline. The original experiment logs, baseline value, variant definitions, and analysis code were not included in the project brief. The demo does not reproduce or independently verify that result.

All catalog items and playground behavior are synthetic. Match, coverage, and freshness values shown in the demo are computed from that synthetic catalog; they are not CTR, experiment results, or user research. The three demo strategies illustrate ranking tradeoffs and are not asserted to be the exact arms used in the original A/B test.

## Proposed next step: reinforcement learning

The page frames reinforcement learning as a possible extension rather than completed work. A credible follow-up would define session state, delayed satisfaction signals, and guardrails for discovery breadth before choosing a reward function or running a contextual-bandit experiment.

## Run the tests

Requires Node.js 18 or later; the tests use only Node's built-in test runner.

```sh
node --test tests/core.test.mjs
```

## Contents

- `index.html` — product story and interactive playground shell
- `styles.css` — responsive visual system
- `app.js` — user interactions and feed rendering
- `recommendation-core.mjs` — deterministic catalog generation, ranking, and proxy metrics
- `tests/core.test.mjs` — tests for catalog size, ranking determinism, diversity, exclusions, and summaries
