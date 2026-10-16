"""Polymarket US spread/total snapshots. No credentials or raw API responses persist."""
from copy import deepcopy
from datetime import datetime, timezone
import math

BOOKMAKER = 'polymarket_us'
TEAM_NAMES = {
    'Arizona Cardinals':'ARI','Atlanta Falcons':'ATL','Baltimore Ravens':'BAL','Buffalo Bills':'BUF',
    'Carolina Panthers':'CAR','Chicago Bears':'CHI','Cincinnati Bengals':'CIN','Cleveland Browns':'CLE',
    'Dallas Cowboys':'DAL','Denver Broncos':'DEN','Detroit Lions':'DET','Green Bay Packers':'GB',
    'Houston Texans':'HOU','Indianapolis Colts':'IND','Jacksonville Jaguars':'JAX','Kansas City Chiefs':'KC',
    'Las Vegas Raiders':'LV','Los Angeles Chargers':'LAC','Los Angeles Rams':'LA','Miami Dolphins':'MIA',
    'Minnesota Vikings':'MIN','New England Patriots':'NE','New Orleans Saints':'NO','New York Giants':'NYG',
    'New York Jets':'NYJ','Philadelphia Eagles':'PHI','Pittsburgh Steelers':'PIT','San Francisco 49ers':'SF',
    'Seattle Seahawks':'SEA','Tampa Bay Buccaneers':'TB','Tennessee Titans':'TEN','Washington Commanders':'WAS',
}
MARKETS = ('spreads','totals')


def instant(value):
    try:
        dt = datetime.fromisoformat(value.replace('Z','+00:00'))
        return dt if dt.tzinfo else None
    except (ValueError, TypeError, AttributeError):
        return None


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def quote(market, event, observed_at, book_updated):
    outcomes = market.get('outcomes', [])
    if not isinstance(outcomes, list):
        return None
    by_name = {o.get('name'): o for o in outcomes if isinstance(o, dict)}
    names = [event['home_team'],event['away_team']] if market['key']=='spreads' else ['Over','Under']
    if any(name not in by_name or not finite(by_name[name].get('point')) for name in names):
        return None
    points = [by_name[n]['point'] for n in names]
    if market['key']=='spreads' and abs(sum(points))>1e-9:
        return None
    if market['key']=='totals' and (abs(points[0]-points[1])>1e-9 or points[0]<0):
        return None
    updated = market.get('last_update') or book_updated
    if not instant(updated) or instant(updated)>instant(observed_at):
        return None
    # Whitelist only quote fields: never copy URLs, request objects, or API keys.
    result = dict(observed_at=observed_at, source_updated_at=updated)
    if market['key']=='spreads':
        result.update(home_point=points[0], away_point=points[1])
    else:
        result['point']=points[0]
    return result


def update_snapshot(events, schedule, previous=None, observed_at=None):
    observed_at = observed_at or datetime.now(timezone.utc).isoformat(timespec='seconds')
    now = instant(observed_at)
    if now is None:
        raise ValueError('Observation time must include a timezone')
    if not isinstance(events,list) or any(not isinstance(e,dict) for e in events):
        raise ValueError('Unexpected odds event format')
    if previous and previous.get('bookmaker') != BOOKMAKER:
        raise ValueError('Refusing to mix bookmaker history')
    if previous and instant(previous.get('fetched_at')) and instant(previous['fetched_at'])>now:
        raise ValueError('Refusing an older fetch over a newer snapshot')
    result = deepcopy(previous) if previous else dict(schema_version=1, season=2026, bookmaker=BOOKMAKER, games={})
    result.update(fetched_at=observed_at, markets_requested=list(MARKETS))
    stats = dict(events_returned=len(events),matched_events=0,unmatched_events=0,spread_quotes=0,total_quotes=0)
    for old in result['games'].values():
        for key in MARKETS:
            old[key]['returned_at_last_check']=False
    for event in events:
        if event.get('sport_key') != 'americanfootball_nfl':
            continue
        home,away=TEAM_NAMES.get(event.get('home_team')),TEAM_NAMES.get(event.get('away_team'))
        kickoff=instant(event.get('commence_time'))
        candidates=[g for g in schedule['games'] if g['home_team']==home and g['away_team']==away
                    and kickoff and instant(g.get('kickoff'))
                    and abs((instant(g['kickoff'])-kickoff).total_seconds())<=86400]
        if len(candidates)!=1:
            stats['unmatched_events']+=1
            continue
        game=candidates[0]
        stats['matched_events']+=1
        entry=result['games'].setdefault(game['game_id'],dict(
            provider_event_id=event.get('id'),home_team=home,away_team=away,
            spreads=dict(first_observed=None,latest=None,returned_at_last_check=False),
            totals=dict(first_observed=None,latest=None,returned_at_last_check=False)))
        # Never capture live or postgame quotes as pregame lines.
        if kickoff<=now:
            continue
        for book in event.get('bookmakers',[]):
            if book.get('key')!=BOOKMAKER:
                continue
            for market in book.get('markets',[]):
                key=market.get('key')
                if key not in MARKETS:
                    continue
                value=quote(market,event,observed_at,book.get('last_update'))
                if value is None:
                    continue
                state=entry[key]
                if state['latest'] and instant(state['latest']['source_updated_at'])>instant(value['source_updated_at']):
                    continue
                if state['first_observed'] is None:
                    state['first_observed']=deepcopy(value)
                state.update(latest=value,returned_at_last_check=True)
                stats['spread_quotes' if key=='spreads' else 'total_quotes']+=1
    result['coverage']=stats
    return result
