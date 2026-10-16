# NFL EPA Lab

A standalone HTML site with **Matchups** as the default view and **EPA Leaderboards** as a second top-level section. The leaderboard has eight dimension tabs, three metric toggles (EPA/play by default), and a horizontal team-distance plot above each table. Best teams are always on the right; defensive EPA allowed reverses the numeric direction. Team labels retain exact EPA coordinates, with vertical separation only to avoid overlaps. Real team logos appear in the plot and table, with names and abbreviations for clarity. Select a team in the plot or table to highlight it. View state is saved in the URL fragment for sharing.

![Matchups site preview](docs/matchups-preview.png)

[Leaderboard preview](docs/preview.png)

## Open the HTML site

Download `docs/index.html` using GitHub’s **Download raw file** button and open it in a browser. The file contains the data, CSS, and JavaScript; no install, backend, network request, or build is required to view it. JavaScript must be enabled.

Alternatively, serve it locally from the repository root:

```sh
python -m http.server 8000 --directory docs
```

For a hosted site, enable **Settings → Pages → Deploy from a branch → main → /docs** in this GitHub repository. The files are ready for Pages, but pushing them does not enable hosting.

## Matchups and the current week

The published 2026 schedule currently has **272 regular-season games across all 18 weeks**. Select a week, step backward/forward, or return to the current week. Games are grouped by the visitor's local calendar date and ordered by kickoff; times include the visitor's timezone abbreviation. Each game shows team logos, away/home roles, saved Polymarket US spread/total panels, and stadium with city/state (or city/country for international games). Venue locations are maintained in `venue_locations.py`, keyed by stadium rather than home team; unknown venues display Location TBD. Bye teams are listed below the slate.

The opening week is calculated in the browser at visit time, not at build time. NFL weeks roll over **Tuesday at midnight America/New_York**, using the first scheduled game of each week to locate that Tuesday. October 16, 2026 selects Week 6. Before the season, Week 1 is selected; after the published season, the final week is selected. Explicit week links preserve the chosen week. The page also checks for a new week while left open.

The schedule is a snapshot, not a live feed. Refresh and rebuild for flex scheduling changes. Unknown kickoff times stay TBD; playoff rounds are included once published by the source. This schedule view does not apply the fixed Week 5 EPA snapshot to historical or future matchups. Leaderboards retain their separate Week 5 scope. Old leaderboard links still work.

## Polymarket US betting quotes

The server-side updater reads `ODDS_API_KEY` from the environment and requests only NFL `spreads,totals` from The Odds API's `polymarket_us` bookmaker. Set the key securely in the execution environment, never in source code, client HTML, or a command-line argument. GitHub Actions would need its own separately configured repository secret if scheduling is added later.

```sh
.venv/bin/python export_odds.py
python build_site.py
```

The build embeds the sanitized `reports/odds_2026.json` snapshot in the HTML. The browser makes no odds API calls and contains no API key. Refresh failures leave the prior snapshot intact. Keep this JSON file between runs: it contains the earliest quote captured and latest observed quote for each market/game. It is intentionally checked in for reproducible, reviewable snapshots. Deleting it resets first-observed history.

**Coverage verified October 16, 2026:** the bookmaker is recognized and supplies moneylines, but returned **zero NFL spread or total quotes**. The saved snapshot correctly shows unavailable markets. Moneylines and other bookmakers are never substituted for the requested spread/total markets. This verifies access, not availability of these two markets.

Quotes are labeled **First observed** and **Last observed**, not opening or live. No historical-opening endpoint has been integrated or verified. Each quote stores capture time and provider update time; unavailable markets retain older quotes with a visible warning. Events map to schedule games by both teams and kickoff (within 24 hours); ambiguous matches are skipped. Only quotes captured before kickoff are accepted. A negative home point means the home team is favored (the reverse of nflverse's `spread_line` convention). UI renders the favored team's abbreviation and spread, or Pick’em. Totals are shown as O/U.

Refreshes are currently **manual**. In validation, requesting two markets cost two API credits; a 30-minute schedule would cost about 96 credits/day. The account reported 495 credits remaining after validation. No recurring job was enabled to spend credits on empty markets. A later scheduled updater must securely load the key, run the exporter/build, retain the snapshot, and publish the generated files. The current static site does not auto-refresh.

## Rebuild the site

```sh
python build_site.py
```

The builder uses the committed EPA CSV, schedule JSON, and export provenance in `reports/` and `web/index.template.html`, producing the self-contained `docs/index.html`. To refresh the data, run the export command below and then rebuild. Edit the template rather than the generated HTML.

Team EPA remains scoped to the **2026 regular season, through Week 5 inclusive**.

[View all eight leaderboards and actual values](reports/epa_2026_through_week_5.md) or [download the full CSV](reports/epa_2026_through_week_5.csv).

## Run the Python dashboard (alternative)

```sh
cd /workspace/nflverse
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/streamlit run app.py --server.address 0.0.0.0
```

Eight dimension tabs: offense pass/rush/total, defense pass/rush/total, special teams possession-side/opponent-side. Every team has total EPA, EPA/play, EPA/game, separate ranks for each measure, play count, and game count. Select the measure to rank and chart; tables are also sortable by clicking headers. All dimensions are downloadable as CSV. Bars retain real EPA distances and are centered on zero.

Offense: higher is better. Defense retains raw EPA allowed: lower is better. Special teams possession-side EPA uses `posteam` and higher is better; opponent-side EPA uses `defteam` and lower is better. These are **not fixed kicking and receiving units**: on kickoffs the receiving team is posteam; on punts the punting team is posteam. Includes punts, kickoffs, field goals and extra points. Possession total minus opponent total produces net special teams EPA. ST EPA/play is exploratory; samples and play mixes differ.

EPA/play = sum of EPA / count of qualifying plays with non-null EPA. EPA/game = sum of EPA / all completed team games in weeks 1–5, including games with no plays in a particular dimension, accounting for byes. No plays yields null EPA/play; no games yields null EPA/game and no rank. Ties use competition ranks. Pass/rush flags follow nflverse, including sacks and scrambles. No garbage-time or opponent adjustments.

Data loads through nflreadpy, refreshed hourly or through the sidebar button. Ignored raw Parquet caches live in `data/raw/`. Only completed games are aggregated; missing play-by-play for completed games blocks the dashboard. Current completeness checks detect entirely missing games, not partial files. The date filter excludes future weeks but uses current stat corrections, not an archived historical snapshot. Network access to GitHub and its release asset hosts is required. Source retrieval time is displayed.

## Export and validate

```sh
.venv/bin/python export_leaderboards.py  # Only when refreshing the Week 5 EPA snapshot
.venv/bin/python export_schedule.py     # Refresh the season schedule independently
python build_site.py
.venv/bin/pytest -q
```

Exports produce the reviewable Markdown/CSV EPA snapshots and `schedule_2026.json` under `reports/`. Kickoff timestamps are converted from nflverse Eastern game times to explicit UTC instants, including daylight saving time, before bundling. These are actual source data, unlike the older fabricated HTML design studies in `prototypes/`. The earlier pregame aggregation API remains in `metrics.py` for future matchup work.

## Browser validation

```sh
.venv/bin/pip install -e ".[dev,browser]"
# Requires system Chromium on PATH (or install Chromium for this machine).
.venv/bin/python tests/browser/check_site.py
.venv/bin/python tests/browser/check_matchups.py
.venv/bin/python tests/browser/check_odds.py
```

The leaderboard browser check serves the static site temporarily and verifies all 24 dimension/metric combinations, exact linear horizontal positions, label separation, correct sorting, keyboard interaction, team highlighting, CSV download, URL state, and mobile overflow.

The matchup browser check covers all 272 games and 18 weeks, chronological ordering, every week rollover including DST, default Week 6, pre/post-season bounds, explicit-week links, week navigation, local kickoff times in Los Angeles and Tokyo, mobile layout, and backward-compatible leaderboard links.

Odds tests cover immutable first observations, line movement, home/away sign conventions, missing markets, stale updates, pregame-only captures, bookmaker isolation, and credential-safe errors. The browser test checks real unavailable states plus injected synthetic quotes (never saved to the product), favorite changes, totals, Pick’em, stale warnings, and no browser API calls.

## Logos

All 32 team logos are bundled as original PNGs from nflverse/nflplotR and embedded in the standalone HTML, so they work offline without CDN access. The build verifies their SHA-256 checksums. See [logo source and attribution](web/assets/logos/README.md) and [source manifest](web/assets/logos/sources.json). Team marks belong to their respective owners.
