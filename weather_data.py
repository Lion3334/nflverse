"""UTC hourly forecasts matched to game kickoff; no historical weather invented."""
from datetime import datetime, timedelta, timezone
from copy import deepcopy
import math
from venue_weather import VENUES

FIELDS = {
    'temperature_2m':'temperature_f', 'apparent_temperature':'feels_like_f',
    'precipitation_probability':'precipitation_probability', 'precipitation':'precipitation_inches',
    'weather_code':'weather_code', 'wind_speed_10m':'wind_mph',
    'wind_gusts_10m':'gust_mph', 'wind_direction_10m':'wind_direction_degrees',
}
CODES={0:'Clear',1:'Mostly clear',2:'Partly cloudy',3:'Overcast',45:'Fog',48:'Rime fog',
       51:'Light drizzle',53:'Drizzle',55:'Heavy drizzle',56:'Freezing drizzle',57:'Freezing drizzle',
       61:'Light rain',63:'Rain',65:'Heavy rain',66:'Freezing rain',67:'Heavy freezing rain',
       71:'Light snow',73:'Snow',75:'Heavy snow',77:'Snow grains',80:'Light showers',81:'Rain showers',
       82:'Heavy showers',85:'Snow showers',86:'Heavy snow showers',95:'Thunderstorm',96:'Thunderstorm with hail',99:'Thunderstorm with hail'}


def instant(value):
    try:
        result=datetime.fromisoformat(value.replace('Z','+00:00'))
        return result if result.tzinfo else None
    except (ValueError,AttributeError,TypeError):return None


def valid(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def nearest_forecast(payload,kickoff,retrieved_at):
    if not isinstance(payload,dict):raise ValueError('Invalid forecast response')
    if payload.get('utc_offset_seconds')!=0:
        raise ValueError('Forecast timezone must be UTC')
    units=payload.get('hourly_units',{})
    expected={'temperature_2m':('°F',),'apparent_temperature':('°F',),
              'wind_speed_10m':('mp/h','mph'),'wind_gusts_10m':('mp/h','mph'),
              'precipitation':('inch',),'precipitation_probability':('%',)}
    hourly=payload.get('hourly',{})
    if not isinstance(hourly,dict) or not isinstance(units,dict):raise ValueError('Invalid hourly forecast')
    for field,allowed in expected.items():
        if field in hourly and units.get(field) not in allowed:
            raise ValueError('Unexpected forecast units')
    candidates=[]
    for index,value in enumerate(hourly.get('time',[])):
        # The API is explicitly requested with timezone=UTC; naive API times are UTC.
        if not isinstance(value,str):continue
        stamp=instant(value if value.endswith(('Z','+00:00')) else value+'+00:00')
        if stamp:candidates.append((abs((stamp-kickoff).total_seconds()),stamp,index))
    if not candidates:return None
    distance,stamp,index=min(candidates)  # Ties use the earlier hour.
    if distance>1800:return None
    result=dict(forecast_time=stamp.isoformat(),retrieved_at=retrieved_at)
    for field,name in FIELDS.items():
        values=hourly.get(field,[])
        value=values[index] if index<len(values) else None
        result[name]=value if valid(value) else None
    if not any(result[name] is not None for name in FIELDS.values()):return None
    result['conditions']=CODES.get(result['weather_code'],'Conditions unavailable')
    return result


def prepare(schedule,previous=None,now=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError('Current time must include a timezone')
    horizon=now.astimezone(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=16)
    snapshot=dict(schema_version=1,provider='Open-Meteo',attempted_at=now.isoformat(timespec='seconds'),
                  forecast_days=16,games={})
    coordinates=set()
    for game in schedule['games']:
        kickoff=instant(game.get('kickoff'));venue=VENUES.get(game.get('stadium'))
        entry=dict(stadium=game.get('stadium'),kickoff=game.get('kickoff'),forecast=None)
        if venue:entry.update(latitude=venue[0],longitude=venue[1],roof=venue[2])
        old=(previous or {}).get('games',{}).get(game['game_id'],{})
        if (old.get('kickoff')==entry['kickoff'] and old.get('stadium')==entry['stadium']
            and (old.get('latitude'),old.get('longitude'))==(entry.get('latitude'),entry.get('longitude'))):
            entry['forecast']=deepcopy(old.get('forecast'))
        if not kickoff:entry['status']='kickoff_unknown'
        elif kickoff<=now:entry['status']='saved_pregame' if entry['forecast'] else 'past_unavailable'
        elif not venue:entry['status']='venue_unknown'
        elif kickoff>=horizon:entry['status']='outside_horizon'
        else:
            entry['status']='pending_fetch'
            coordinates.add(venue[:2])
        snapshot['games'][game['game_id']]=entry
    return snapshot,sorted(coordinates)


def apply_forecasts(snapshot,payloads):
    """payloads maps (latitude, longitude) to a response, or None on failure."""
    for entry in snapshot['games'].values():
        if entry['status']!='pending_fetch':continue
        payload=payloads.get((entry['latitude'],entry['longitude']))
        if payload is None:
            entry['status']='stale_forecast' if entry['forecast'] else 'fetch_failed'
            continue
        try:
            forecast=nearest_forecast(payload,instant(entry['kickoff']),snapshot['attempted_at'])
        except (ValueError,TypeError,KeyError):forecast=None
        if forecast:
            entry.update(status='available',forecast=forecast)
        else:entry['status']='stale_forecast' if entry['forecast'] else 'forecast_unavailable'
    snapshot['coverage']={status:sum(g['status']==status for g in snapshot['games'].values())
                           for status in sorted({g['status'] for g in snapshot['games'].values()})}
    return snapshot
