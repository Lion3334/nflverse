# Matchup design study

These are review-only mockups. No product files, navigation, schedule, or leaderboard behavior have changed.

- [A: Possession cards](mock-a.png): two panels, one for each team's offense facing the other defense. The clearest detail view, with sample counts.
- [B: Unit matrix](mock-b.png): both directions in one table. The most compact option for scanning. Bars encode league rank, not numeric EPA distance.
- [C: Shared EPA scales](mock-c.png): the offense and opposing defense plotted on the same raw EPA axis, with values and ranks. Each row's range comes from all teams in the corresponding offensive and defensive dimension. Higher is better for offense, lower for defense; dot separation is not a forecast.

All three use actual Seattle/Denver values from the committed 2026-through-Week-5 snapshot, with total EPA, EPA/play (default), and EPA/game toggles. Both possession-side/opponent-side special teams comparisons are shown. These are historical team metrics, not projected matchup results.

Download `epa-matchup-mocks.html` using GitHub's Download raw file button and open it locally to switch layouts/metrics. It is standalone, including the logos. For local HTTP viewing: `python -m http.server 8001 --directory designs` and open `/epa-matchup-mocks.html`.

Regenerate from the current committed snapshot and assets with `python designs/build_matchup_mocks.py`. Edit `matchup.template.html` for design changes. This build only writes inside `designs/`.

## Compact weekly possession-table mock

[Weekly preview](compact-weekly-preview.png) · [Seattle–Denver close-up](compact-game-preview.png) · [Mobile preview](compact-mobile-preview.png) · [Interactive HTML](compact-matchup-mock.html)

This follow-up uses the actual 14-game Week 6 schedule and the through-Week-5 EPA snapshot. Each game has two tables side by side: Total, Pass, Rush columns, with possessing offense and opposing defense as rows. Each of the six cells displays the selected EPA value and its league rank. On mobile, the two possession tables stack.

The shared selector switches Total EPA, EPA/play (default), and EPA/game. Heat-map color is a continuous red-to-neutral-to-green scale by league rank, independently for each dimension and measure. Rank 1 is green and rank 32 red. Defensive colors follow lower-is-better ranks, not raw EPA signs. Values and ranks remain visible. No predictions or composite matchup advantage are calculated. Special teams is outside these six-cell scrimmage tables.

Regenerate with `python designs/build_compact_mock.py`. This only writes inside `designs/`; the product is unchanged.
