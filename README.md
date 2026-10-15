# NFL Matchup Lab

A personal NFL EPA dashboard for weekly matchup research. No predictions or betting recommendations.

```sh
cd /workspace/nflverse
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/streamlit run app.py --server.address 0.0.0.0
```

Use the weekly matchup, game detail, and leaderboard tabs. Select a season and week in the sidebar. Historical matchups use regular-season plays strictly before the selected week; season 2026 includes the regular season leading into 2027. Week 1 has no ratings. Idle teams retain their season-to-date ratings. Rank ties use competition ranking.

Offense and defense use EPA/play, including sacks and scrambles according to nflverse pass/rush flags. Defensive EPA retains its raw sign: lower is better. Special teams sums possession-side EPA minus opponent-side EPA, divided by distinct games played. No garbage-time or opponent adjustments.

Data loads through nflreadpy and is refreshed hourly or via the refresh button, with raw Parquet copies in ignored `data/raw/`. Initial startup requires access to nflverse sources on GitHub and its release asset hosts. Thursday morning refreshes generally include more stat corrections. Historical views exclude future weeks but use the latest corrected data, not archived as-of snapshots.

Run `.venv/bin/pytest -q` for aggregation tests. HTML design studies are in `prototypes/`; their data is fabricated and separate from the dashboard.
