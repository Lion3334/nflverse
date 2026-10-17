# NFL EPA Lab — project context

Architecture, data contracts, hosting, and validation commands live in [HANDOFF.md](HANDOFF.md) and [README.md](README.md). This file records session state only. Edit `web/index.template.html`, then run `.venv/bin/python build_site.py`; never hand-edit `docs/index.html`.

## Current status (2026-10-16)

Shipped to `main` this session (all pushed, deploy via GitHub Pages workflow not yet confirmed by me):
- Leaderboard plot: alternating above/below-axis logo callouts on one axis (was ~1,100px tall, now ~440–520px). Exact x positions kept; defense still puts best on the right.
- Dimension selector: three separate cards (Offense / Defense / Special teams), selected tab solid green.
- Domed stadiums: games at the 10 listed venues show "Domed stadium · roof type · weather not shown" instead of weather.
- Matchup heat maps: red–green "extremes emphasized" rank scale (mock option D), legend gradient matches.
- Odds panel: compact hairline table, Latest before Open, right column capped at 250px, source/quote-time text in a small "ⓘ Source & quote times" expander.

Local setup now exists: `.venv` created (gitignored), `pytest` = 57 passing. Mock files live outside the repo in `/Users/eastcoastlimited/ClaudeCode/nflverse-mocks/`.

## Decisions made (don't re-litigate)

- Leaderboard plot layout = mock B (alternating callouts), logo-only boxes (no abbreviation text).
- Selector = option 1 (separate cards). Heat map = option D (red–green, extremes emphasized); the blue–orange scale was shipped briefly, then replaced.
- Domed list: Superdome, Ford Field, Allegiant, SoFi, U.S. Bank (fixed); AT&T, Lucas Oil, Mercedes-Benz, NRG (nflverse name "Reliant Stadium"), State Farm (retractable). Display-only: the weather refresh job still fetches forecasts for these venues, by user instruction. Bernabeu (Madrid, retractable) is not on the user's list and still shows weather.
- Odds: Latest on the left, Open on the right.

## Open items

- Logos intermittently render blank in the leaderboard chart after a re-render (see next.md #1).
- User said the new odds layout leaves room beside the odds column for "more data" — not yet specified what.
- Not confirmed: that the Pages deploys for this session's pushes succeeded, and the live site shows the new layouts.
- `tests/browser/check_site.py` and `check_odds.py` have not been run since these changes (Chrome crashed on launch with sandbox errors under Playwright here; the scripts look for a `chromium` binary on PATH).

## Tried and dropped

- Mocks A (packed number line), C (ranked bars), D (heat strip) for the plot — user chose B.
- Selector options 2–4 (two-step, grid, color-coded groups) — user chose 1.
- Heat map options A, B (blue–orange, shipped then reverted), C (stepped) — user chose D.
- Odds options 1–3 (slim grid, one-liner, tiles) — user chose a compacted version of 4.

## Key context

- User is a non-technical PM: explain terminal commands in plain English; show mocks/screenshots before building; ask before pushing (push only when told).
- Always `git fetch origin main` and check `HEAD..FETCH_HEAD` before pushing — bots commit snapshots to main. Never force-push.
- macOS `sed -i` needs a backup-suffix argument; use Python for in-place edits.
- Embedded logos are 500×500 PNGs (~1.5MB of the 2.5MB page), drawn at ~22–32px.
