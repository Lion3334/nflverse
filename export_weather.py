"""Refresh free Open-Meteo forecasts for upcoming games within 16 days."""
import json
from pathlib import Path
import requests
from weather_data import FIELDS,prepare,apply_forecasts

ROOT=Path(__file__).resolve().parent


def fetch_forecasts(coordinates):
    if not coordinates:return {}
    params=dict(latitude=','.join(str(c[0]) for c in coordinates),longitude=','.join(str(c[1]) for c in coordinates),
                hourly=','.join(FIELDS),temperature_unit='fahrenheit',wind_speed_unit='mph',
                precipitation_unit='inch',timezone='UTC',forecast_days=16)
    try:
        r=requests.get('https://api.open-meteo.com/v1/forecast',params=params,timeout=60)
        if r.status_code!=200:
            print(f'Open-Meteo HTTP {r.status_code}; existing forecasts retained where valid.')
            return {coordinate:None for coordinate in coordinates}
        payload=r.json()
        items=payload if isinstance(payload,list) else [payload]
        if len(items)!=len(coordinates):raise ValueError('Coordinate result count mismatch')
        result={}
        for coordinate,item in zip(coordinates,items):
            # API grid points can differ slightly from requested stadium coordinates.
            if not isinstance(item,dict) or abs(item.get('latitude',999)-coordinate[0])>.5 or abs(item.get('longitude',999)-coordinate[1])>.5:
                result[coordinate]=None
            else:result[coordinate]=item
        return result
    except (requests.RequestException,ValueError,TypeError):
        print('Open-Meteo request failed; existing forecasts retained where valid.')
        return {coordinate:None for coordinate in coordinates}


def export():
    path=ROOT/'reports/weather_2026.json'
    previous=json.loads(path.read_text()) if path.exists() else None
    schedule=json.loads((ROOT/'reports/schedule_2026.json').read_text())
    snapshot,coordinates=prepare(schedule,previous)
    snapshot=apply_forecasts(snapshot,fetch_forecasts(coordinates))
    temporary=path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(snapshot,indent=2,allow_nan=False)+'\n')
    temporary.replace(path)
    print('Weather snapshot:',json.dumps(snapshot['coverage']))
    print('Unique stadium forecast locations requested:',len(coordinates))
    return snapshot


if __name__=='__main__':
    export()
