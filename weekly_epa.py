"""Advance EPA only after Tuesday rollover and complete prior-week source data."""
import json
from datetime import datetime, timezone
from pathlib import Path

from metrics import missing_games
from export_leaderboards import write_reports

ROOT = Path(__file__).resolve().parent


class SourceNotReady(ValueError):
    """Prior-week source data is incomplete; expected for a while after a Tuesday rollover."""


def target_week(schedule, now):
    return max((w['week'] for w in schedule['weeks'] if w['game_type'] == 'REG'
                and datetime.fromisoformat(w['end']) <= now), default=0)


def validate_history(pbp, schedule, through_week, season=2026):
    import polars as pl
    games = schedule.filter((pl.col('season') == season) & (pl.col('game_type') == 'REG')
                            & (pl.col('week') <= through_week))
    if not games.height or games.filter(pl.col('home_score').is_null() | pl.col('away_score').is_null()).height:
        raise SourceNotReady('Prior-week schedule still contains unfinished games; retaining previous EPA')
    missing = missing_games(pbp, schedule, season, through_week)
    if missing:
        raise SourceNotReady(f'Missing completed-game play-by-play: {missing}')
    usable = pbp.filter(pl.col('epa').is_not_null()).get_column('game_id').unique().to_list()
    if set(games['game_id'].to_list()) - set(usable):
        raise SourceNotReady('Completed games lack non-null EPA; retaining previous EPA')


def refresh(now=None):
    now = now or datetime.now(timezone.utc)
    schedule = json.loads((ROOT / 'reports/schedule_2026.json').read_text())
    target = target_week(schedule, now)
    manifest_path = ROOT / 'reports/epa_snapshot.json'
    current = json.loads(manifest_path.read_text())
    if target <= current['through_week']:
        print(f'EPA already through Week {current["through_week"]}; no advance due')
        return
    import nflreadpy as nfl
    from metrics import leaderboard
    season = schedule['season']
    source_schedule = nfl.load_schedules([season])
    pbp = nfl.load_pbp([season])
    validate_history(pbp, source_schedule, target, season)
    frame = leaderboard(pbp, source_schedule, season, target)
    # Immutable published snapshots preserve prior matchup views; never overwrite archives.
    if (ROOT / f'reports/epa_{season}_through_week_{target}.csv').exists():
        raise ValueError('Target archive already exists; review before changing published EPA')
    write_reports(frame, ROOT / 'reports', season=season, through_week=target)
    manifest_path.write_text(json.dumps({'season': season, 'through_week': target,
                                       'exported_at': now.isoformat()}, indent=2) + '\n')
    print(f'Advanced EPA through Week {target}')


if __name__ == '__main__':
    try:
        refresh()
    except SourceNotReady as error:
        # Retain the prior snapshot and let the next scheduled run retry; other errors fail the job.
        print(f'::warning::EPA advance deferred: {error}')
