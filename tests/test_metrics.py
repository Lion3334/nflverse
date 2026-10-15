import polars as pl
import pytest
from metrics import ratings


def play(week, epa, **overrides):
    return dict(season=2026, week=week, season_type="REG", game_id=f"g{week}",
                posteam="GB", defteam="CHI", epa=float(epa),
                **{"pass": 1, "rush": 0, "play_type": "pass"}) | overrides


def test_weighted_pregame_ratings_and_defensive_sign():
    data = pl.DataFrame([play(1, 2), play(2, 0), play(2, 0), play(3, 100)])
    rows = {r['team']: r for r in ratings(data, 2026, 3, ['GB', 'CHI', 'BUF']).to_dicts()}
    assert rows['GB']['off'] == pytest.approx(2 / 3)
    assert rows['CHI']['def'] == rows['GB']['off']
    assert rows['GB']['games'] == 2
    assert rows['BUF']['off'] is None


def test_special_teams_net_and_bye_carry_forward():
    data = pl.DataFrame([play(1, 6, **{'pass': 0, 'play_type': 'kickoff'}), play(1, 0)])
    rows = {r['team']: r for r in ratings(data, 2026, 3, ['GB', 'CHI']).to_dicts()}
    assert rows['GB']['st'] == 6
    assert rows['CHI']['st'] == -6
    assert sum(r['st_total'] for r in rows.values()) == 0


def test_season_and_postseason_excluded_and_week_one_empty():
    data = pl.DataFrame([play(1, 1), play(1, 90, season=2025), play(1, 90, season_type='POST')])
    assert ratings(data, 2026, 2, ['GB', 'CHI']).filter(pl.col('team') == 'GB')['off'][0] == 1
    assert ratings(data, 2026, 1, ['GB', 'CHI'])['off'].null_count() == 2


def test_defense_ranks_lower_values_first():
    data = pl.DataFrame([play(1, -1), play(1, 1, posteam='CHI', defteam='GB')])
    frame = ratings(data, 2026, 2, ['GB', 'CHI'])
    assert frame.filter(pl.col('team') == 'CHI')['def_rank'][0] == 1
