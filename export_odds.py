"""Fetch Polymarket US NFL spreads/totals without exposing the API key."""
import json
import os
from pathlib import Path
import sys

import requests
from odds_data import BOOKMAKER, update_snapshot

ROOT=Path(__file__).resolve().parent


def fetch_events():
    key=os.environ.get('ODDS_API_KEY')
    if not key:
        raise RuntimeError('ODDS_API_KEY is not available; configure it securely in environment settings.')
    try:
        response=requests.get('https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/',
            params=dict(apiKey=key,bookmakers=BOOKMAKER,markets='spreads,totals',oddsFormat='american',dateFormat='iso'),timeout=30)
    except requests.RequestException:
        raise RuntimeError('Odds request failed; existing snapshot preserved.') from None
    if response.status_code!=200:
        raise RuntimeError(f'Odds API returned HTTP {response.status_code}; existing snapshot preserved.')
    try:
        events=response.json()
    except ValueError:
        raise RuntimeError('Odds API returned invalid JSON; existing snapshot preserved.') from None
    # Quota metadata only; request URLs and response text must never be logged.
    usage={k:response.headers.get(k) for k in ('x-requests-last','x-requests-remaining')}
    return events,usage


def export():
    events,usage=fetch_events()
    output=ROOT/'reports/odds_2026.json'
    previous=json.loads(output.read_text()) if output.exists() else None
    schedule=json.loads((ROOT/'reports/schedule_2026.json').read_text())
    snapshot=update_snapshot(events,schedule,previous)
    temporary=output.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(snapshot,indent=2,allow_nan=False)+'\n')
    temporary.replace(output)
    print('Saved Polymarket US snapshot:',json.dumps(snapshot['coverage']))
    print('API quota:',json.dumps(usage))
    if not snapshot['coverage']['spread_quotes'] and not snapshot['coverage']['total_quotes']:
        print('No spreads or totals returned. Missing markets remain unavailable; no other bookmaker substituted.')


if __name__=='__main__':
    try:
        export()
    except (RuntimeError,ValueError,OSError):
        # Print only our known-safe RuntimeError messages, not parser/OS details.
        error=sys.exception()
        print(str(error) if type(error) is RuntimeError else 'Snapshot validation or save failed; no successful refresh recorded.',file=sys.stderr)
        sys.exit(1)
