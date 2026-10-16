import pytest
from odds_data import update_snapshot
from export_odds import fetch_events

SCHEDULE={'games':[{'game_id':'2026_06_SEA_DEN','home_team':'DEN','away_team':'SEA','kickoff':'2026-10-18T20:00:00Z'}]}
NOW='2026-10-16T19:00:00Z'


def event(home_point=-3.5,total=44.5,book='polymarket_us',updated='2026-10-16T18:50:00Z'):
    return {'id':'event-1','sport_key':'americanfootball_nfl','home_team':'Denver Broncos','away_team':'Seattle Seahawks',
            'commence_time':'2026-10-18T20:00:00Z','bookmakers':[{'key':book,'last_update':updated,'markets':[
                {'key':'spreads','outcomes':[{'name':'Denver Broncos','point':home_point},{'name':'Seattle Seahawks','point':-home_point}]},
                {'key':'totals','outcomes':[{'name':'Over','point':total},{'name':'Under','point':total}]}]}]}


def state(snapshot):
    return snapshot['games']['2026_06_SEA_DEN']


def test_first_observed_immutable_latest_updates_with_raw_home_sign():
    first=update_snapshot([event()],SCHEDULE,observed_at=NOW)
    latest=update_snapshot([event(-4.5,45.5,updated='2026-10-16T19:10:00Z')],SCHEDULE,first,'2026-10-16T19:15:00Z')
    assert state(latest)['spreads']['first_observed']['home_point']==-3.5
    assert state(latest)['spreads']['latest']['home_point']==-4.5
    assert state(latest)['spreads']['latest']['away_point']==4.5
    assert state(latest)['totals']['first_observed']['point']==44.5
    assert state(latest)['totals']['latest']['point']==45.5
    assert state(first)['spreads']['latest']['home_point']==-3.5


def test_unavailable_market_preserves_history_but_marks_no_current_quote():
    first=update_snapshot([event()],SCHEDULE,observed_at=NOW)
    empty=event();empty['bookmakers']=[]
    later=update_snapshot([empty],SCHEDULE,first,'2026-10-16T20:00:00Z')
    assert state(later)['spreads']['latest']==state(first)['spreads']['latest']
    assert state(later)['spreads']['returned_at_last_check'] is False
    assert later['coverage']['spread_quotes']==0


def test_other_book_and_moneyline_never_substituted():
    wrong=update_snapshot([event(book='other_book')],SCHEDULE,observed_at=NOW)
    assert state(wrong)['spreads']['latest'] is None
    moneyline=event();moneyline['bookmakers'][0]['markets']=[{'key':'h2h','outcomes':[]}]
    assert state(update_snapshot([moneyline],SCHEDULE,observed_at=NOW))['totals']['latest'] is None


@pytest.mark.parametrize('change', ['inconsistent_spread','inconsistent_total','nan','future_timestamp'])
def test_invalid_quotes_rejected(change):
    data=event()
    markets=data['bookmakers'][0]['markets']
    if change=='inconsistent_spread':markets[0]['outcomes'][0]['point']=99
    if change=='inconsistent_total':markets[1]['outcomes'][0]['point']=99
    if change=='nan':markets[0]['outcomes'][0]['point']=float('nan')
    if change=='future_timestamp':data['bookmakers'][0]['last_update']='2026-10-17T20:00:00Z'
    result=state(update_snapshot([data],SCHEDULE,observed_at=NOW))
    target='totals' if change=='inconsistent_total' else 'spreads'
    assert result[target]['latest'] is None


def test_post_kickoff_and_unmatched_event_not_captured():
    late=update_snapshot([event()],SCHEDULE,observed_at='2026-10-19T00:00:00Z')
    assert state(late)['spreads']['latest'] is None
    wrong=event();wrong['away_team']='Chicago Bears'
    result=update_snapshot([wrong],SCHEDULE,observed_at=NOW)
    assert result['games']=={} and result['coverage']['unmatched_events']==1


def test_older_source_cannot_replace_latest_quote():
    first=update_snapshot([event()],SCHEDULE,observed_at=NOW)
    result=update_snapshot([event(-10,updated='2026-10-16T18:00:00Z')],SCHEDULE,first,'2026-10-16T20:00:00Z')
    assert state(result)['spreads']['latest']['home_point']==-3.5


def test_api_error_and_network_exception_do_not_expose_key(monkeypatch):
    import requests
    monkeypatch.setenv('ODDS_API_KEY','fake-sensitive-value')
    def failure(*args,**kwargs):raise requests.RequestException('url?apiKey=fake-sensitive-value')
    monkeypatch.setattr(requests,'get',failure)
    with pytest.raises(RuntimeError) as error:fetch_events()
    assert 'fake-sensitive-value' not in str(error.value)
    class Response:
        status_code=401
    monkeypatch.setattr(requests,'get',lambda *a,**k:Response())
    with pytest.raises(RuntimeError,match='HTTP 401') as error:fetch_events()
    assert 'fake-sensitive-value' not in str(error.value)


def test_missing_key_and_wrong_book_history_rejected(monkeypatch):
    monkeypatch.delenv('ODDS_API_KEY',raising=False)
    with pytest.raises(RuntimeError,match='not available'):fetch_events()
    with pytest.raises(ValueError,match='mix bookmaker'):update_snapshot([],SCHEDULE,{'bookmaker':'other'},NOW)
