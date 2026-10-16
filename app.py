from datetime import datetime, timezone
from pathlib import Path

import altair as alt
import polars as pl
import streamlit as st
from metrics import DIMENSIONS, MEASURES, leaderboard, missing_games

SEASON, THROUGH_WEEK = 2026, 5
st.set_page_config(page_title="NFL EPA Leaderboards", layout="wide")
st.title("NFL EPA Leaderboards")
st.caption("2026 regular season · Through Week 5 inclusive · Latest corrected data")

@st.cache_data(ttl=3600, show_spinner="Loading nflverse data…")
def load(season):
    import nflreadpy as nfl
    root = Path(__file__).parent / "data" / "raw"
    root.mkdir(parents=True, exist_ok=True)
    pbp = nfl.load_pbp([season])
    schedule = nfl.load_schedules([season])
    pbp.write_parquet(root / f"pbp_{season}.parquet")
    schedule.write_parquet(root / f"schedule_{season}.parquet")
    return pbp, schedule, datetime.now(timezone.utc).isoformat(timespec="seconds")

if st.sidebar.button("Refresh source data"):
    load.clear()
try:
    pbp, schedule, loaded_at = load(SEASON)
except Exception as exc:
    st.error("NFL data could not be loaded. Check source availability and network access, then refresh.")
    st.exception(exc)
    st.stop()
missing = missing_games(pbp, schedule, SEASON, THROUGH_WEEK)
if missing:
    st.error(f"Incomplete source: {len(missing)} completed games have no play-by-play. Rankings withheld.")
    st.write(missing)
    st.stop()
if schedule.filter((pl.col("season") == SEASON) & (pl.col("game_type") == "REG")
                   & (pl.col("week") == THROUGH_WEEK) & pl.col("home_score").is_not_null()).is_empty():
    st.error("Week 5 results are not available. Rankings withheld.")
    st.stop()
frame = leaderboard(pbp, schedule, SEASON, THROUGH_WEEK)
st.caption(f"Source retrieved {loaded_at} · nflverse via nflreadpy · {frame['team'].n_unique()} teams")
st.info("Offense and possession-side special teams: higher is better. Defense and opponent-side special teams EPA allowed: lower is better. #1 is best; ties share ranks.")
st.caption("EPA/game = total EPA ÷ all completed team games through Week 5, accounting for byes. EPA/100 plays = EPA/play × 100, using only qualifying plays with non-null EPA. No garbage-time or opponent adjustments.")
measure = st.selectbox("Rank and chart by", list(MEASURES), index=1, format_func=MEASURES.get)
tabs = st.tabs([spec[0] for spec in DIMENSIONS.values()])
for tab, (key, (label, side, kind, lower_better)) in zip(tabs, DIMENSIONS.items()):
    with tab:
        st.subheader(label)
        if kind == "st":
            st.caption("These are possession roles, not pure kicking/receiving units. On kickoffs the receiving team is posteam; on punts the punting team is posteam. Includes punts, kickoffs, field goals and extra points. Opponent values retain the possession team's EPA sign.")
            st.caption("Special teams EPA/100 plays is provided for exploration; small samples and differing play mixes limit comparisons.")
        st.caption(f"{MEASURES[measure]} · {'Lower' if lower_better else 'Higher'} is better")
        ranked = frame.filter(pl.col("dimension") == key).sort(
            [measure, "team"], descending=[not lower_better, False], nulls_last=True)
        columns = ["team", "games", "plays"]
        for m in MEASURES:
            columns.extend([m, m + "_rank"])
        config = {"team": "Team", "games": "Games", "plays": "Plays"}
        for m, title in MEASURES.items():
            config[m] = st.column_config.NumberColumn(title, format="%.2f" if m == "epa_per_100_plays" else "%.3f")
            config[m + "_rank"] = st.column_config.NumberColumn(title + " rank", format="%d")
        st.dataframe(ranked.select(columns), hide_index=True, width="stretch", height=700, column_config=config)
        chart_data = ranked.select("team", measure).to_dicts()
        order = ranked["team"].to_list()
        chart = alt.Chart(alt.Data(values=chart_data)).mark_bar().encode(
            y=alt.Y("team:N", sort=order, title=None),
            x=alt.X(f"{measure}:Q", title=MEASURES[measure], scale=alt.Scale(zero=True)),
            color=alt.condition(f"datum.{measure} >= 0", alt.value("#319d87"), alt.value("#9c7ac7")),
            tooltip=[alt.Tooltip("team:N", title="Team"), alt.Tooltip(f"{measure}:Q", format=".3f")],
        ).properties(height=760)
        zero = alt.Chart(alt.Data(values=[{"zero": 0}])).mark_rule(color="#8291a4").encode(x="zero:Q")
        st.altair_chart(chart + zero, width="stretch")
        st.caption("Bars show actual EPA relative to zero. Color indicates sign, not quality.")
        st.download_button("Download this dimension", ranked.write_csv(),
                           f"epa_{SEASON}_through_week_{THROUGH_WEEK}_{key}.csv", "text/csv", key=key)
st.download_button("Download all eight dimensions", frame.write_csv(),
                   "epa_2026_through_week_5.csv", "text/csv")
