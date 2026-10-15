"""Pregame, season-to-date EPA. Defensive values retain the offense's sign."""
import polars as pl

ST_TYPES = ["punt", "kickoff", "field_goal", "extra_point"]
METRICS = {
    "off": "Offensive EPA/play", "off_pass": "Offensive pass EPA/play",
    "off_rush": "Offensive rush EPA/play", "def": "Defensive EPA allowed/play",
    "def_pass": "Defensive pass EPA allowed/play", "def_rush": "Defensive rush EPA allowed/play",
    "st": "Special teams net EPA/game",
}


def scrimmage_filter():
    return ((pl.col("pass") == 1) | (pl.col("rush") == 1)) & pl.col("epa").is_not_null()


def ratings(pbp, season, week, teams):
    """Use only completed earlier regular-season weeks; include idle teams."""
    history = pbp.filter((pl.col("season") == season) & (pl.col("week") < week)
                         & (pl.col("season_type") == "REG"))
    result = pl.DataFrame({"team": sorted(set(teams))}, schema={"team": pl.String})
    scrim = history.filter(scrimmage_filter())
    for side, prefix in [("posteam", "off"), ("defteam", "def")]:
        for suffix, extra in [("", pl.lit(True)), ("_pass", pl.col("pass") == 1),
                              ("_rush", pl.col("rush") == 1)]:
            key = prefix + suffix
            group = scrim.filter(extra & pl.col(side).is_not_null()).group_by(side).agg(
                pl.col("epa").sum().alias(key + "_total"),
                pl.len().alias(key + "_plays"),
            ).rename({side: "team"})
            result = result.join(group, on="team", how="left").with_columns(
                (pl.col(key + "_total") / pl.col(key + "_plays")).alias(key))
    st = history.filter(pl.col("play_type").is_in(ST_TYPES) & pl.col("epa").is_not_null())
    parts = []
    for side, sign in [("posteam", 1), ("defteam", -1)]:
        parts.append(st.select(pl.col(side).alias("team"), (pl.col("epa") * sign).alias("epa")))
    totals = pl.concat(parts).group_by("team").agg(pl.col("epa").sum().alias("st_total"))
    games = pl.concat([history.select(pl.col(side).alias("team"), "game_id")
                       for side in ["posteam", "defteam"]]).drop_nulls().unique().group_by("team").len(name="games")
    result = result.join(games, on="team", how="left").join(totals, on="team", how="left").with_columns(
        (pl.col("st_total").fill_null(0) / pl.col("games")).alias("st"))
    return result.with_columns([
        pl.col(key).rank(method="min", descending=not key.startswith("def")).alias(key + "_rank")
        for key in METRICS
    ])
