from pathlib import Path
import polars as pl
import streamlit as st
from metrics import METRICS, ratings

st.set_page_config(page_title="NFL Matchup Lab", layout="wide")
st.title("NFL Matchup Lab")
st.caption("Season-to-date efficiency · Matchups, not predictions")

@st.cache_data(ttl=3600, show_spinner="Loading nflverse data…")
def load(season):
    import nflreadpy as nfl
    root = Path(__file__).parent / "data" / "raw"
    root.mkdir(parents=True, exist_ok=True)
    pbp = nfl.load_pbp([season])
    schedule = nfl.load_schedules([season])
    pbp.write_parquet(root / f"pbp_{season}.parquet")
    schedule.write_parquet(root / f"schedule_{season}.parquet")
    return pbp, schedule

season = st.sidebar.number_input("Season", 1999, 2026, 2026)
if st.sidebar.button("Refresh source data"):
    load.clear()
try:
    pbp, schedule = load(season)
except Exception as exc:
    st.error("NFL data could not be loaded. Check source availability and network access, then refresh.")
    st.exception(exc)
    st.stop()
st.caption(f"Source coverage: play-by-play through Week {pbp['week'].max()} · {pbp.height:,} source plays. Historical views use the latest stat corrections.")
schedule = schedule.filter(pl.col("game_type") == "REG")
weeks = sorted(schedule["week"].unique().to_list())
completed = schedule.filter(pl.col("home_score").is_not_null())
default = min(int(completed["week"].max() or 0) + 1, max(weeks))
week = st.sidebar.selectbox("Matchup week", weeks, index=weeks.index(default))
st.caption(f"{season} regular season · Week {week} · Ratings use weeks 1–{week - 1} only" if week > 1 else f"{season} · Week 1 · No season-to-date results yet")
st.info("Offense: higher EPA/play is better. Defense allowed: lower is better. Special teams: higher net EPA/game is better. Rank #1 is best; ties share a rank.")
teams = set(schedule["home_team"].to_list() + schedule["away_team"].to_list())
frame = ratings(pbp, season, week, teams)
lookup = {r["team"]: r for r in frame.to_dicts()}

def display(value, rank):
    return "—" if value is None else f"{value:+.3f} · #{int(rank)}"

def matchup(away, home):
    for offense, defense in [(away, home), (home, away)]:
        st.markdown(f"**{offense} offense → {defense} defense**")
        rows = []
        for label, suffix in [("Overall", ""), ("Pass", "_pass"), ("Rush", "_rush")]:
            a, b = lookup[offense], lookup[defense]
            x, y = "off" + suffix, "def" + suffix
            rows.append({"Unit": label, f"{offense} offense EPA/play · rank": display(a[x], a[x + "_rank"]),
                         "Offensive plays": a[x + "_plays"],
                         f"{defense} defense allowed/play · rank": display(b[y], b[y + "_rank"]),
                         "Defensive plays": b[y + "_plays"]})
        st.dataframe(rows, hide_index=True, width="stretch")
    st.markdown("**Special teams · net EPA/game**")
    cols = st.columns(2)
    for col, team in zip(cols, [away, home]):
        row = lookup[team]
        col.metric(team, display(row["st"], row["st_rank"]))
        col.caption(f"{row['games'] or 0} games · Net EPA total: {row['st_total'] or 0:+.2f}")

slate, detail, leaders = st.tabs(["Weekly matchups", "Game detail", "EPA leaderboard"])
games = schedule.filter(pl.col("week") == week).sort("game_id").to_dicts()
with slate:
    for game in games:
        with st.expander(f"{game['away_team']} at {game['home_team']} · {game.get('gameday', '')}"):
            matchup(game["away_team"], game["home_team"])
with detail:
    choices = {f"{g['away_team']} at {g['home_team']}": g for g in games}
    if choices:
        selected = st.selectbox("Matchup", list(choices))
        g = choices[selected]
        matchup(g["away_team"], g["home_team"])
with leaders:
    key = st.selectbox("EPA field", list(METRICS), format_func=METRICS.get)
    ranked = frame.sort(key, descending=not key.startswith("def"), nulls_last=True)
    table = ranked.select(pl.col(key + "_rank").alias("Rank"), "team", pl.col(key).alias("EPA"))
    st.dataframe(table, hide_index=True, width="stretch")
    st.bar_chart(table.drop_nulls(), x="team", y="EPA", horizontal=True, sort=False)
    st.caption("Bars show actual EPA values relative to zero. Negative defensive EPA is favorable.")
    st.download_button("Download ratings CSV", frame.write_csv(), f"ratings_{season}_before_week_{week}.csv", "text/csv")
