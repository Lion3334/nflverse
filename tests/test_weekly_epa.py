from datetime import datetime
import json
from pathlib import Path
import polars as pl
import pytest
from weekly_epa import target_week, validate_history

SCHEDULE = json.loads((Path(__file__).parents[1] / 'reports/schedule_2026.json').read_text())

@pytest.mark.parametrize('moment,expected', [
    ('2026-09-01T12:00:00+00:00',0),
    ('2026-10-20T03:59:59+00:00',5),
    ('2026-10-20T04:00:00+00:00',6),
    ('2026-11-03T04:59:59+00:00',7),
    ('2026-11-03T05:00:00+00:00',8),
    ('2027-02-01T12:00:00+00:00',18),
])
def test_tuesday_rollover_and_dst(moment,expected):
    assert target_week(SCHEDULE,datetime.fromisoformat(moment)) == expected


def test_incomplete_source_keeps_prior_snapshot():
    schedule = pl.DataFrame({'season':[2026], 'game_type':['REG'], 'week':[6],
                             'game_id':['g'], 'home_score':[None], 'away_score':[7]})
    pbp = pl.DataFrame({'season':[2026], 'season_type':['REG'], 'week':[6],
                        'game_id':['g'], 'epa':[1.0]})
    with pytest.raises(ValueError,match='unfinished'):
        validate_history(pbp,schedule,6)
    complete = schedule.with_columns(pl.lit(10).alias('home_score'))
    with pytest.raises(ValueError,match='Missing completed-game'):
        validate_history(pbp.head(0),complete,6)
    with pytest.raises(ValueError,match='non-null EPA'):
        validate_history(pbp.with_columns(pl.lit(None).alias('epa')),complete,6)
    validate_history(pbp,complete,6)
