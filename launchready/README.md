# LaunchReady

**From first playtest to confident launch** — an independent Roblox creator-focused product management case study and working web prototype by Amulya Ravikumar.

**[Read the case study](CASE_STUDY.md) · [Open the prototype](dist/index.html) · [View the four-slide deck](deck/LaunchReady_4_slide_case_study.pptx)**

![LaunchReady overview](screenshots/overview-desktop.jpg)

## What this project does

LaunchReady explores a proposed workflow for a first-time creator reviewing a small, private playtest. The prototype lets a creator:

- Set one specific learning question during onboarding.
- Add, search, filter, and triage feedback by journey stage, theme, severity, and status.
- Compare candidate fixes with editable, illustrative RICE-style inputs.
- Review a launch checklist and unresolved high-severity issues.
- Export feedback to CSV, keep changes in browser local storage, and reset the demo.

Every player note, count, funnel value, and example experience is **synthetic**. This is **not affiliated with Roblox**, connected to Roblox APIs, or a claim of creator interviews, measured impact, or A/B test results.

## Run locally

The app is static HTML, CSS, and JavaScript. It has no runtime dependencies.

```sh
python3 -m http.server 8765 -d dist
```

Then open `http://localhost:8765/`. The full portfolio page is at `http://localhost:8765/case-study.html`.

## Test

The browser smoke test covers onboarding, feedback intake and search, readiness, priority editing, persistence, mobile layout, and the case-study page.

```sh
npm install
npx playwright install chromium
npm run test:smoke
```

Start the local server in another terminal before running the test. To use a local Chrome binary instead of Playwright's browser, set `CHROME_PATH` to its executable path. Set `LAUNCHREADY_URL` to test another URL. Test screenshots go to `test-output/` by default.

## Project structure

- `dist/` — deployable website
- `CASE_STUDY.md` — research boundaries, PRD, prioritization, metrics, experiment design, safety, and GTM
- `deck/` — concise four-slide overview
- `screenshots/` — desktop and mobile views
- `tests/` — browser smoke test

## Source context

Roblox's [October 12, 2026 announcement](https://devforum.roblox.com/t/a-simpler-path-to-publish-plus-invite-early-testers/4930524) described a gradual guided-publishing rollout and the ability for eligible creators to invite up to 10 early testers. The product premise and its limits are detailed in the [case study](CASE_STUDY.md). The [Roblox Creator Hub analytics](https://create.roblox.com/docs/production/analytics) and [experiment documentation](https://create.roblox.com/docs/production/experiments) informed the metrics and experiment proposal.

Created for Amulya's Summer 2027 PM internship portfolio. Roblox names and links are used only to identify the public platform context.
