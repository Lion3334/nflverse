from copy import deepcopy
from datetime import datetime, timezone
import pytest
from weather_data import prepare,apply_forecasts,nearest_forecast
from export_weather import fetch_forecasts
from venue_weather import VENUES

NOW=datetime(2026,10,16,19,tzinfo=timezone.utc)
GAME={'game_id':'g','kickoff':'2026-10-18T17:30:00Z','stadium':'Wembley Stadium','home_team':'JAX'}
SCHEDULE={'games':[GAME]}


def payload():
    return {'utc_offset_seconds':0,'latitude':51.55,'longitude':-.28,
            'hourly_units':{'temperature_2m':'°F','apparent_temperature':'°F','precipitation_probability':'%',
                            'precipitation':'inch','wind_speed_10m':'mp/h','wind_gusts_10m':'mp/h'},
            'hourly':{'time':['2026-10-18T17:00','2026-10-18T18:00'],
                      'temperature_2m':[60,62],'apparent_temperature':[58,60],
                      'precipitation_probability':[30,40],'precipitation':[.01,.02],
                      'weather_code':[3,61],'wind_speed_10m':[10,12],
                      'wind_gusts_10m':[20,22],'wind_direction_10m':[270,280]}}


def test_utc_nearest_hour_tie_earlier_and_units():
    f=nearest_forecast(payload(),datetime(2026,10,18,17,30,tzinfo=timezone.utc),NOW.isoformat())
    assert f['temperature_f']==60 and f['conditions']=='Overcast'
    assert f['forecast_time']=='2026-10-18T17:00:00+00:00'
    assert f['wind_mph']==10 and f['precipitation_inches']==.01


def test_no_hour_outside_half_hour_or_wrong_units():
    assert nearest_forecast(payload(),NOW,NOW.isoformat()) is None
    bad=payload();bad['hourly_units']['temperature_2m']='°C'
    with pytest.raises(ValueError,match='units'):nearest_forecast(bad,NOW,NOW.isoformat())
    bad=payload();bad['utc_offset_seconds']=3600
    with pytest.raises(ValueError,match='UTC'):nearest_forecast(bad,NOW,NOW.isoformat())


def test_international_location_from_stadium_not_home_team_and_deduped():
    schedule={'games':[GAME,dict(GAME,game_id='g2')]}
    snapshot,coords=prepare(schedule,now=NOW)
    assert coords==[VENUES['Wembley Stadium'][:2]]
    done=apply_forecasts(snapshot,{coords[0]:payload()})
    assert done['coverage']=={'available':2}
    assert done['games']['g']['latitude']>50


def test_past_horizon_unknown_and_roof_status():
    games=[dict(GAME,game_id='past',kickoff='2026-10-15T17:00:00Z'),
           dict(GAME,game_id='far',kickoff='2026-12-01T17:00:00Z'),
           dict(GAME,game_id='time',kickoff=None),dict(GAME,game_id='venue',stadium='Unknown'),
           dict(GAME,game_id='roof',stadium='AT&T Stadium'),dict(GAME,game_id='dome',stadium='Ford Field')]
    result,_=prepare({'games':games},now=NOW)
    assert result['games']['past']['status']=='past_unavailable'
    assert result['games']['far']['status']=='outside_horizon'
    assert result['games']['time']['status']=='kickoff_unknown'
    assert result['games']['venue']['status']=='venue_unknown'
    assert result['games']['roof']['roof']=='retractable'
    assert result['games']['dome']['roof']=='indoor'


def test_refresh_failure_preserves_forecast_and_archives_after_kickoff():
    initial,coords=prepare(SCHEDULE,now=NOW)
    first=apply_forecasts(initial,{coords[0]:payload()})
    later,coords=prepare(SCHEDULE,first,now=NOW)
    failed=apply_forecasts(later,{coords[0]:None})
    assert failed['games']['g']['status']=='stale_forecast'
    assert failed['games']['g']['forecast']==first['games']['g']['forecast']
    past,coords=prepare(SCHEDULE,first,now=datetime(2026,10,19,tzinfo=timezone.utc))
    assert not coords and past['games']['g']['status']=='saved_pregame'


def test_changed_kickoff_does_not_keep_wrong_forecast():
    snap,coords=prepare(SCHEDULE,now=NOW)
    first=apply_forecasts(snap,{coords[0]:payload()})
    updated={'games':[dict(GAME,kickoff='2026-10-18T20:00:00Z')]}
    new,coords=prepare(updated,first,now=NOW)
    failed=apply_forecasts(new,{coords[0]:None})
    assert failed['games']['g']['forecast'] is None


def test_missing_fields_render_null_not_zero_and_http_failure(monkeypatch):
    import requests
    partial=payload();partial['hourly']['wind_gusts_10m']=[None,None]
    f=nearest_forecast(partial,datetime(2026,10,18,17,30,tzinfo=timezone.utc),NOW.isoformat())
    assert f['gust_mph'] is None
    def fail(*a,**k):raise requests.RequestException('network blocked')
    monkeypatch.setattr(requests,'get',fail)
    assert fetch_forecasts([(51.55,-.28)])=={(51.55,-.28):None}


def test_successful_batched_request_contract_and_coordinate_mapping(monkeypatch):
    import requests
    coordinates=[(51.556,-.2796),(39.7439,-105.0201)]
    first=payload();second=deepcopy(first);second.update(latitude=39.75,longitude=-105.0)
    class Response:
        status_code=200
        def json(self):return [first,second]
    def get(url,params,timeout):
        assert url=='https://api.open-meteo.com/v1/forecast'
        assert params['timezone']=='UTC' and params['forecast_days']==16
        assert params['temperature_unit']=='fahrenheit' and params['wind_speed_unit']=='mph'
        assert params['precipitation_unit']=='inch' and 'apiKey' not in params
        assert len(params['latitude'].split(','))==2
        return Response()
    monkeypatch.setattr(requests,'get',get)
    result=fetch_forecasts(coordinates)
    assert result[coordinates[0]]['latitude']==51.55
    assert result[coordinates[1]]['latitude']==39.75
