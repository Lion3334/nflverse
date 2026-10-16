from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from odds_schedule import due_mode, opening_target, LATEST_CRON, LATEST_CRONS, OPENING_CRON
from odds_data import update_snapshot
from test_odds import event, state

PACIFIC=ZoneInfo('America/Los_Angeles')
SCHEDULE={'weeks':[{'key':'REG-6','start':'2026-10-13T04:00:00Z'}],
          'games':[{'game_id':'2026_06_SEA_DEN','week_key':'REG-6','home_team':'DEN','away_team':'SEA','kickoff':'2026-10-18T20:00:00Z'}]}


def test_weekly_opening_is_previous_sunday_midnight_pacific():
    assert opening_target(SCHEDULE['weeks'][0]).isoformat()=='2026-10-11T07:00:00+00:00'
    assert opening_target({'start':'2026-11-10T05:00:00Z'}).isoformat()=='2026-11-08T08:00:00+00:00'


@pytest.mark.parametrize('day',['2026-07-05','2026-11-08','2026-03-08','2026-11-01'])
def test_exactly_two_latest_slots_per_pacific_day_including_dst(day):
    start=datetime.fromisoformat(day).replace(tzinfo=PACIFIC).astimezone(timezone.utc)
    end=(datetime.fromisoformat(day)+timedelta(days=1)).replace(tzinfo=PACIFIC).astimezone(timezone.utc)
    hours=[];moment=start
    while moment<end:
        for cron in LATEST_CRONS:
            if moment.hour in (0,11,12,23) and due_mode(moment,cron=cron)=='latest':
                hours.append(moment.astimezone(PACIFIC).hour)
        moment+=timedelta(hours=1)
    assert hours==[4,16]


@pytest.mark.parametrize('stamp,expected',[
    ('2026-10-18T07:02:00Z','opening'),('2026-10-18T08:02:00Z','skip'),
    ('2026-11-08T07:02:00Z','skip'),('2026-11-08T08:02:00Z','opening'),
    ('2026-10-18T07:16:00Z','skip'),('2026-10-19T07:02:00Z','skip')])
def test_sunday_gate_and_late_jobs(stamp,expected):
    assert due_mode(datetime.fromisoformat(stamp.replace('Z','+00:00')),cron=OPENING_CRON)==expected


def test_manual_run_is_latest_never_backfills_opening():
    assert due_mode(datetime.now(timezone.utc),event_name='workflow_dispatch')=='latest'
    snapshot=update_snapshot([event(updated='2026-10-11T06:59:00Z')],SCHEDULE,observed_at='2026-10-11T07:05:00Z')
    assert state(snapshot)['spreads']['opening'] is None


def test_opening_saved_once_and_latest_moves_independently():
    first=update_snapshot([event(updated='2026-10-11T06:59:00Z')],SCHEDULE,
                          observed_at='2026-10-11T07:05:00Z',capture_opening=True)
    latest=update_snapshot([event(-4.5,45.5)],SCHEDULE,first,'2026-10-16T19:00:00Z')
    assert state(latest)['spreads']['opening']['home_point']==-3.5
    assert state(latest)['spreads']['latest']['home_point']==-4.5
    assert state(latest)['totals']['opening']['point']==44.5
    assert state(latest)['totals']['latest']['point']==45.5


@pytest.mark.parametrize('observed,updated',[
    ('2026-10-11T07:16:00Z','2026-10-11T06:59:00Z'),
    ('2026-10-11T07:05:00Z','2026-10-11T07:01:00Z'),
    ('2026-10-11T06:59:00Z','2026-10-11T06:58:00Z'),
    ('2026-10-16T19:00:00Z','2026-10-16T18:50:00Z')])
def test_late_newer_or_wrong_day_quotes_never_substitute_for_opening(observed,updated):
    result=update_snapshot([event(updated=updated)],SCHEDULE,observed_at=observed,capture_opening=True)
    assert state(result)['spreads']['opening'] is None
    assert state(result)['totals']['opening'] is None


def test_delayed_wrong_dst_candidate_and_duplicate_hour_do_not_fetch():
    now=datetime.fromisoformat('2026-11-08T12:05:00+00:00')
    assert due_mode(now,cron=LATEST_CRONS[0])=='skip'
    assert due_mode(now,cron=LATEST_CRONS[1])=='latest'
    assert due_mode(now,cron=LATEST_CRONS[1],last_fetched_at='2026-11-08T12:01:00Z')=='skip'
