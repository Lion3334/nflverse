# Collaborator handoff

Updated October 16, 2026. Start here, then read [README.md](README.md) for operational details.

## What we are building

A personal NFL research dashboard for understanding matchups and informing low-stakes CBS/Sleeper pick'em choices. The user prefers a compact league-wide view with actual EPA values and league ranks, without tiers, predictions, or extra contextual features yet.

The primary product is the static, self-contained `docs/index.html`, generated from `web/index.template.html` by `build_site.py`. Edit the template, then rebuild; do not hand-edit generated HTML. `app.py` is an alternative Streamlit implementation, not the primary experience. Older `designs/` and `prototypes/` are exploration artifacts.

Current approved interface:

- Matchups is the default section; EPA Leaderboards is the second section.
- Week selection defaults by visitor date; NFL week rollover is Tuesday midnight America/New_York. Explicit shared week links override the default. All 272 regular-season games / 18 weeks are bundled; games are grouped and sorted in the visitor's local timezone.
- Each game has two possession tables (Total / Pass / Rush, offense versus defense) and a 2×2 special teams table (possession / opponent EPA). Cells show values and ranks, colored by rank.
- Eight leaderboard dimensions, three shared metric options: Total EPA, **EPA/100 plays (default)**, EPA/game. EPA/100 plays is raw EPA/play × 100, with identical ranks. Defense and opponent ST use lower-is-better rankings. Leaderboard plots put best teams on the right with exact EPA distances.
- Real bundled NFL logos; kickoff and stadium/city/state beside teams; FanDuel Open/Latest spread and total on the right.
- Latest design cleanup removes promotional copy and repeated metric labels. Weather details, quote timestamps, and source/methodology explanations expand in place. Preserve all data while keeping the default view compact.

## Data contracts and limitations

**EPA advances automatically after Tuesday rollover.** `weekly_epa.py` checks the completed prior week at the 4 a.m. Pacific refresh, retrying subsequent refreshes when source data is delayed. `reports/epa_snapshot.json` selects the latest immutable weekly CSV/Markdown archive. The builder embeds saved snapshots; historical matchups select the latest cutoff strictly before their week. Weeks without an earlier archive remain blank. Initial archive: Week 5. First planned advance: October 20, through Week 6. Corrected nflverse data is not original game-day data.

EPA calculations/ranks: `metrics.py`; export: `export_leaderboards.py`; report: `reports/epa_2026_through_week_5.csv` and matching Markdown. Raw `epa_per_play` remains for compatibility. EPA/game uses completed team games including games with no qualifying plays. ST possession/opponent are nflverse posteam/defteam roles, not fixed kicking/returning units: receiver possesses kickoffs; punter possesses punts. No opponent/garbage-time adjustments.

Schedule: `export_schedule.py`, `schedule_data.py`, `reports/schedule_2026.json`. Stadium location mappings: `venue_locations.py`. Schedule is bundled and must be refreshed/rebuilt for flex changes, TBD times, and eventual postseason additions.

Odds: `odds_data.py`, `export_odds.py`, `odds_schedule.py`, `reports/odds_2026.json`. Use **FanDuel (`fanduel`) via The Odds API**. Polymarket US did not provide our requested spreads/totals during testing; its separate report is historical exploration, not a fallback. The saved FanDuel snapshot has 24 matched events with both requested markets, fetched October 16. Latest-line capture targets **4 a.m. and 4 p.m. America/Los_Angeles**. "Opening" specifically means **Sunday midnight Pacific before that NFL week**, not sportsbook first listing. Provider update must be at/before cutoff, collected within 15 minutes. No retroactive openings; unavailable stays unavailable. Week 7 opening target: October 18. Preserve first-observed and opening history; never replace unavailable markets with another book. GitHub cron is best effort and can miss this window.

Weather: `weather_data.py`, `export_weather.py`, `venue_weather.py`, `reports/weather_2026.json`. Free Open-Meteo, no key, server-side only. Approximate stadium coordinates, nearest hourly forecast within 30 minutes of kickoff, 16-day horizon, Fahrenheit/mph/inches. Indoor/retractable/covered fields need outside-weather and roof caveats; roof position is unknown. Preserve saved pregame forecasts; never fetch a new forecast for a past game. Null fields remain unavailable. Initial local access was blocked, but remote commit **35a5578** successfully saved **28 available forecasts** (164 outside horizon, 80 past without saved forecast). This confirms a successful remote weather fetch, not by itself a successful Pages deployment or recurring schedule.

## Hosting and automation

Expected Pages address: https://lion3334.github.io/nflverse/ — verify reachability and deployed revision; do not assume it is live based on a Git push.

`.github/workflows/refresh-odds.yml` (**Refresh NFL odds and weather**) is already committed. It refreshes weather independently of odds credentials, captures quotes, rebuilds HTML, and commits changed snapshots. Conditional Pages deployment follows a changed refresh when repository variable `PUBLISH_PAGES` is `true`. It currently does not deploy on every ordinary code push; account for this when releasing UI changes. A refresh with no changed output skips deployment.

Repository settings required:

1. Settings → Pages → Source: **GitHub Actions**.
2. Actions repository **variable** `PUBLISH_PAGES` = `true`.
3. Actions repository **secret** `ODDS_API_KEY` = the user's Odds API key. Cloud secrets do not transfer automatically. Never put keys in source, HTML, logs, or chat. Weather needs no key; GitHub supplies deployment authentication.
4. Actions enabled, workflow writes to main allowed, and any `github-pages` environment protection requirements satisfied.

The user confirmed deployment is live. Git transport works here, but GitHub REST API calls returned Forbidden, preventing settings inspection or remote run control. Verify status in the GitHub Actions UI if API access remains unavailable. Cloud allowlists and GitHub-runner networking are separate.

## Development and validation

Python 3.12+. Use the existing checkout; a worktree is unnecessary. Existing `.venv` works in this environment. Fresh setup:

```sh
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev,browser]'
.venv/bin/python -m playwright install chromium
.venv/bin/python build_site.py
.venv/bin/python -m pytest -q
```

Browser scripts use `shutil.which('chromium')`: install system Chromium or adjust discovery to use Playwright's installed executable on a new machine. Serve `docs/` locally for manual review (`python -m http.server 8000 --directory docs`). The shipped file also opens offline.

Existing browser checks (each starts its own local HTTP server):

```sh
.venv/bin/python tests/browser/check_matchup_tables.py
.venv/bin/python tests/browser/check_matchups.py
.venv/bin/python tests/browser/check_odds.py
.venv/bin/python tests/browser/check_weather.py
.venv/bin/python tests/browser/check_site.py
```

Browser fixtures are injected in memory only: never save synthetic odds/weather into production reports. Some cloud environments require permission for browser/local-server sockets. Prior validation: 50 pytest tests; matchup tables, schedule, odds, weather, and leaderboard checks. The four matchup-related browser checks passed after the compact-layout change. Revalidate after edits and report actual runs, not historical counts as new results.

Manual refreshes (network and source availability required):

```sh
.venv/bin/python export_schedule.py
.venv/bin/python export_weather.py
.venv/bin/python export_odds.py
.venv/bin/python build_site.py
```

EPA export is explicitly Week 5: review scope before running `export_leaderboards.py`. Do not run network refreshes solely to test formatting. Preserve logo/weather attribution and report provenance.

## Recommended next work, in order

1. **Check the live site after releases.** Deployment is confirmed live by the user. Check Pages settings, repository variable, secret presence (never value), and the current deploy run. Confirm deployed HTML includes the compact three-table layout and weather from the remote snapshot. Test the public URL on desktop/mobile. If stuck, inspect the precise failing/waiting step and environment approvals.
2. **Make releases predictable.** Consider a dedicated Pages workflow triggered on `docs/` pushes and manual dispatch so code-only UI changes deploy without a data refresh. Coordinate with the current conditional deploy job to avoid concurrent/redundant deployments. This is a proposed improvement, not already implemented.
3. **Verify scheduled operation.** Confirm 4 a.m./4 p.m. PT refreshes and Sunday opening capture execute, commit, and publish; odds secret is configured; failed API calls preserve prior data and show warnings. Inspect API quota. Weather fetch success is already evidenced, but recurring runs and updated FanDuel captures still require verification.
4. **Verify the first Tuesday EPA advance.** User authorized advancing every Tuesday after MNF. Confirm October 20 produces a through-Week-6 snapshot, publishes it, and retains Week 6 matchup values from the Week 5 archive. Delayed source data should retain the last snapshot and retry.
5. **Iterate on real usage.** Retain compactness, inspect mobile expanders and heatmap readability, and gather user feedback before adding extra context, projections, pick recommendations, tiers, or other features.

Keep main current without overwriting bot updates: fetch the actual `main` ref, inspect changes, fast-forward/rebase appropriately, then push. In this environment `git fetch origin main` updated `FETCH_HEAD` but not `origin/main`; compare against `FETCH_HEAD` or explicitly update the remote-tracking ref. Never force-push over snapshot history.
