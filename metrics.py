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


DIMENSIONS = {
    "off_pass": ("Offense — Pass", "posteam", "pass", False),
    "off_rush": ("Offense — Rush", "posteam", "rush", False),
    "off_total": ("Offense — Total", "posteam", None, False),
    "def_pass": ("Defense — Pass", "defteam", "pass", True),
    "def_rush": ("Defense — Rush", "defteam", "rush", True),
    "def_total": ("Defense — Total", "defteam", None, True),
    "st_possession": ("Special Teams — Possession team", "posteam", "st", False),
    "st_opponent": ("Special Teams — Opponent", "defteam", "st", True),
}
MEASURES = {"total_epa": "Total EPA", "epa_per_play": "EPA/play", "epa_per_game": "EPA/game"}


def leaderboard(pbp, schedule, season=2026, through_week=5):
    """Long-form team ratings, inclusive cutoff, denominator = all games played.

    ST possession/opponent describe nflverse posteam/defteam, not fixed kicking
    and receiving units. Opponent-side EPA is allowed, retaining its raw sign.
    """
    history = pbp.filter((pl.col("season") == season) & (pl.col("week") <= through_week)
                         & (pl.col("season_type") == "REG"))
    regular = schedule.filter((pl.col("season") == season) & (pl.col("game_type") == "REG"))
    completed = regular.filter((pl.col("week") <= through_week)
                              & pl.col("home_score").is_not_null()
                              & pl.col("away_score").is_not_null())
    teams = pl.concat([regular.select(pl.col(side).alias("team"))
                       for side in ["home_team", "away_team"]]).unique().sort("team")
    played = pl.concat([completed.select(pl.col(side).alias("team"), "game_id")
                        for side in ["home_team", "away_team"]]).unique()
    games = played.group_by("team").len(name="games")
    # Ignore partial games: only aggregate games marked completed in schedules.
    history = history.join(completed.select("game_id").unique(), on="game_id", how="semi")
    base = teams.join(games, on="team", how="left").with_columns(pl.col("games").fill_null(0))
    frames = []
    for key, (label, side, kind, lower_better) in DIMENSIONS.items():
        condition = (pl.col("play_type").is_in(ST_TYPES) & pl.col("epa").is_not_null()
                     if kind == "st" else scrimmage_filter())
        if kind in ("pass", "rush"):
            condition &= pl.col(kind) == 1
        totals = history.filter(condition & pl.col(side).is_not_null()).group_by(side).agg(
            pl.col("epa").sum().alias("total_epa"), pl.len().alias("plays")
        ).rename({side: "team"})
        frame = base.join(totals, on="team", how="left").with_columns(
            pl.col("total_epa").fill_null(0), pl.col("plays").fill_null(0)
        ).with_columns(
            pl.when(pl.col("plays") > 0).then(pl.col("total_epa") / pl.col("plays")).alias("epa_per_play"),
            pl.when(pl.col("games") > 0).then(pl.col("total_epa") / pl.col("games")).alias("epa_per_game"),
            pl.lit(key).alias("dimension"), pl.lit(label).alias("label"),
        ).with_columns([
            # No rank for a team with no completed games.
            pl.when(pl.col("games") > 0).then(pl.col(measure)).rank(
                method="min", descending=not lower_better).alias(measure + "_rank")
            for measure in MEASURES
        ])
        frames.append(frame)
    return pl.concat(frames)


def missing_games(pbp, schedule, season=2026, through_week=5):
    expected = schedule.filter((pl.col("season") == season) & (pl.col("game_type") == "REG")
        & (pl.col("week") <= through_week) & pl.col("home_score").is_not_null()
        & pl.col("away_score").is_not_null()).select("game_id").unique()
    actual = pbp.filter((pl.col("season") == season) & (pl.col("season_type") == "REG")
                       & (pl.col("week") <= through_week)).select("game_id").unique()
    return expected.join(actual, on="game_id", how="anti")["game_id"].to_list()
