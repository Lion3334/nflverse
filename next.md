# Next up

1. **Shrink embedded team logos to fix intermittent blank logos.** Logos are 500×500 PNGs (~1.5MB of the 2.5MB `index.html`) drawn at ~22–32px; the chart is rebuilt on every tab/metric change and the browser re-decodes them, so the boxes appear before the logos. Plan: resize to ~128px inside `build_site.py` (Pillow), keep the sha256 manifest check on the original files, check the GitHub Actions workflows install Pillow (add to `pyproject.toml` deps if needed). Verify by repeatedly re-rendering the chart and confirming logos paint immediately; show the user before pushing.
2. **Decide what goes in the space beside the odds column.** User wants "more data" there; they haven't said what. Ask.
3. **Verify the deployed site (suggested).** Confirm Pages deploys for the recent pushes succeeded and the live URL shows the new plot, selector, dome labels, heat map and odds panel; check phone width.
4. **Run the browser checks (suggested).** `check_site.py`, `check_odds.py`, etc. haven't been run since the plot/odds changes; get Playwright to launch a browser here (or a `chromium` on PATH) and fix any assertions tied to the old plot (`.point`) or odds markup.
5. **Existing HANDOFF priorities.** First Tuesday EPA advance (Oct 20, through Week 6), scheduled 4am/4pm PT odds/weather refreshes, Sunday-midnight opening capture (Oct 18).
