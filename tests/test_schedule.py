from datetime import datetime, timezone

from schedule_data import schedule_payload


def game(game_id='g', week=6, day='2026-10-18', clock='13:00', **extras):
    return dict(game_id=game_id, season=2026, game_type='REG', week=week,
                gameday=day, gametime=clock, away_team='GB', home_team='CHI',
                stadium='Soldier Field', location='Home') | extras


def test_eastern_kickoff_conversion_handles_daylight_saving():
    payload = schedule_payload([game(), game('later', 9, '2026-11-08')])
    assert payload['games'][0]['kickoff'] == '2026-10-18T17:00:00+00:00'
    assert payload['games'][1]['kickoff'] == '2026-11-08T18:00:00+00:00'


def test_week_starts_tuesday_eastern_and_extends_past_monday():
    payload = schedule_payload([game(day='2026-10-15', clock='20:15'),
                                game('monday', day='2026-10-19'),
                                game('next', 7, '2026-10-22')])
    six, seven = payload['weeks']
    assert six['start'] == '2026-10-13T04:00:00+00:00'
    assert six['end'] == seven['start'] == '2026-10-20T04:00:00+00:00'
    assert seven['end'] == '2026-10-27T04:00:00+00:00'


def test_tbd_time_is_not_invented_and_games_sort_chronologically():
    payload = schedule_payload([game('tbd', clock=None), game('late', clock='20:15'), game('early')])
    assert [g['game_id'] for g in payload['games']] == ['early', 'late', 'tbd']
    assert payload['games'][-1]['kickoff'] is None


def test_postseason_rounds_and_season_filter():
    payload = schedule_payload([game(), game('post', 19, '2027-01-16', game_type='WC'),
                                game('other', season=2025)])
    assert len(payload['games']) == 2
    assert payload['weeks'][-1]['label'] == 'Wild Card'
    assert payload['weeks'][-1]['key'] == 'WC-19'
