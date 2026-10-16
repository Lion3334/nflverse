"""Create a timezone-aware static season schedule from nflverse."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo('America/New_York')
ROUND_NAMES = {'REG': 'Week', 'WC': 'Wild Card', 'DIV': 'Divisional', 'CON': 'Conference Championships', 'SB': 'Super Bowl'}


def schedule_payload(records, season=2026):
    games, grouped = [], {}
    for row in records:
        if row['season'] != season or row['game_type'] not in ROUND_NAMES:
            continue
        kind, number = row['game_type'], int(row['week'])
        key = f'{kind}-{number}'
        day, clock = row.get('gameday'), row.get('gametime')
        kickoff = None
        if day and clock:
            moment = datetime.combine(date.fromisoformat(day), time.fromisoformat(clock), EASTERN)
            kickoff = moment.astimezone(timezone.utc).isoformat()
        label = f'Week {number}' if kind == 'REG' else ROUND_NAMES[kind]
        game = dict(game_id=row['game_id'], week_key=key, week=number, game_type=kind,
                    gameday=day, kickoff=kickoff, away_team=row['away_team'],
                    home_team=row['home_team'], stadium=row.get('stadium'),
                    neutral=row.get('location') == 'Neutral')
        games.append(game)
        grouped.setdefault(key, dict(key=key, week=number, game_type=kind, label=label, days=[]))['days'].append(day)
    if not games:
        raise ValueError(f'No published schedule for {season}')
    if len({g['game_id'] for g in games}) != len(games):
        raise ValueError('Duplicate scheduled game IDs')
    weeks = []
    for group in grouped.values():
        days = [date.fromisoformat(d) for d in group.pop('days') if d]
        if not days:
            raise ValueError('Cannot determine the NFL week without game dates')
        first = min(days)
        # NFL week rolls over Tuesday at midnight Eastern, before the opening game.
        start = first - timedelta(days=(first.weekday() - 1) % 7)
        group.update(start=datetime.combine(start, time(), EASTERN).astimezone(timezone.utc).isoformat(),
                     first_day=first.isoformat(), last_day=max(days).isoformat())
        weeks.append(group)
    weeks.sort(key=lambda w: (w['start'], w['week']))
    for index, group in enumerate(weeks):
        last = date.fromisoformat(group['last_day'])
        end = last + timedelta(days=(1 - last.weekday()) % 7 or 7)
        group['end'] = weeks[index + 1]['start'] if index + 1 < len(weeks) else datetime.combine(end, time(), EASTERN).astimezone(timezone.utc).isoformat()
    games.sort(key=lambda g: (g['gameday'] or '9999', g['kickoff'] is None, g['kickoff'] or '', g['game_id']))
    return dict(season=season, weeks=weeks, games=games)
