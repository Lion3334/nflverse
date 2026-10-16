import polars as pl
import pytest
from metrics import leaderboard, missing_games
from test_metrics import play


def schedule():
    return pl.DataFrame([
        dict(season=2026, week=w, game_type='REG', game_id=f'g{w}',
             home_team='GB', away_team='CHI', home_score=10, away_score=7)
        for w in [1, 2, 6]
    ])


def test_inclusive_cutoff_and_three_measures():
    pbp = pl.DataFrame([play(1, 2), play(2, 0), play(2, 0), play(6, 100)])
    result = leaderboard(pbp, schedule(), through_week=5)
    row = result.filter((pl.col('team') == 'GB') & (pl.col('dimension') == 'off_pass')).to_dicts()[0]
    assert row['total_epa'] == 2
    assert row['plays'] == 3
    assert row['games'] == 2  # A bye does not count as a game.
    assert row['epa_per_play'] == pytest.approx(2 / 3)
    assert row['epa_per_100_plays'] == pytest.approx(200 / 3)
    assert row['epa_per_100_plays_rank'] == row['epa_per_play_rank']
    assert row['epa_per_game'] == 1
    assert result.height == 16  # Two teams, eight dimensions.


def test_special_teams_roles_raw_sign_and_denominators():
    pbp = pl.DataFrame([play(1, 6, **{'pass': 0, 'play_type': 'kickoff'}),
                        play(1, -2, posteam='CHI', defteam='GB', **{'pass': 0, 'play_type': 'punt'}),
                        play(2, 0)])
    result = leaderboard(pbp, schedule())
    possession = result.filter((pl.col('team') == 'GB') & (pl.col('dimension') == 'st_possession')).to_dicts()[0]
    opponent = result.filter((pl.col('team') == 'GB') & (pl.col('dimension') == 'st_opponent')).to_dicts()[0]
    assert possession['total_epa'] == 6
    assert possession['epa_per_play'] == 6
    assert possession['epa_per_100_plays'] == 600
    assert possession['epa_per_game'] == 3  # All games, not only games with ST plays.
    assert opponent['total_epa'] == -2
    assert opponent['epa_per_play'] == -2
    assert opponent['epa_per_100_plays'] == -200
    assert opponent['epa_per_100_plays_rank'] == opponent['epa_per_play_rank']
    assert opponent['epa_per_game'] == -1
    assert opponent['epa_per_game_rank'] == 1


def test_empty_categories_no_divide_by_zero_and_rank_ties():
    result = leaderboard(pl.DataFrame([play(1, 1), play(2, 2)]), schedule())
    rush = result.filter(pl.col('dimension') == 'off_rush')
    assert rush['plays'].to_list() == [0, 0]
    assert rush['epa_per_play'].null_count() == 2
    assert rush['epa_per_100_plays'].null_count() == 2
    assert rush['total_epa_rank'].to_list() == [1, 1]
    assert rush['epa_per_game'].to_list() == [0, 0]


def test_missing_completed_game_is_detected():
    pbp = pl.DataFrame([play(1, 2)])
    assert missing_games(pbp, schedule()) == ['g2']


def test_partial_game_postseason_and_other_season_excluded():
    pbp = pl.DataFrame([play(1, 1), play(2, 100), play(1, 100, season=2025),
                        play(1, 100, season_type='POST')])
    games = schedule().with_columns(pl.when(pl.col('week') == 2).then(None).otherwise(pl.col('home_score')).alias('home_score'))
    row = leaderboard(pbp, games).filter((pl.col('team') == 'GB') & (pl.col('dimension') == 'off_total')).to_dicts()[0]
    assert row['total_epa'] == 1
    assert row['games'] == 1
