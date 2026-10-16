"""Export a reviewable Week 5 snapshot from freshly retrieved nflverse data."""
from datetime import datetime, timezone
from pathlib import Path

import nflreadpy as nfl
import polars as pl
from metrics import DIMENSIONS, MEASURES, leaderboard, missing_games


def export(pbp, schedule, output=Path('reports')):
    missing = missing_games(pbp, schedule)
    if missing:
        raise ValueError(f'Missing play-by-play for completed games: {missing}')
    frame = leaderboard(pbp, schedule)
    write_reports(frame, output)
    return frame


def write_reports(frame, output=Path('reports'), provenance=None, season=2026, through_week=5):
    output.mkdir(exist_ok=True, parents=True)
    frame.write_csv(output / f'epa_{season}_through_week_{through_week}.csv')
    lines = [f'# NFL team EPA — {season} through Week {through_week}', '',
             provenance or f'Exported {datetime.now(timezone.utc).isoformat(timespec="seconds")} from nflverse via nflreadpy.', '',
             f'Regular season, weeks 1–{through_week} inclusive, completed games only. Latest corrected data at export; published snapshot retained for historical matchup views.', '',
             'EPA/game divides total EPA by all completed team games, accounting for byes. EPA/100 plays equals EPA/play multiplied by 100; ranks are unchanged. Raw EPA/play fields remain in the CSV for compatibility. No opponent or garbage-time adjustments.', '',
             'All tables below are ordered by EPA/100 plays. Each measure has its own rank; #1 is best and ties share a rank.', '',
             'Special teams possession/opponent are nflverse posteam/defteam roles, not fixed kicking/receiving units: the receiving team is posteam on kickoffs, while the punting team is posteam on punts. Opponent EPA retains the raw allowed sign. ST EPA/100 plays is exploratory because samples and play mixes differ.', '']
    for key, (label, _, _, lower) in DIMENSIONS.items():
        subset = frame.filter(pl.col('dimension') == key).sort(['epa_per_100_plays', 'team'], descending=[not lower, False], nulls_last=True)
        lines += [f'## {label}', '', f'{"Lower" if lower else "Higher"} is better for all three measures.', '',
                  '| Team | Games | Plays | Total EPA | Rank | EPA/100 plays | Rank | EPA/game | Rank |',
                  '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
        for row in subset.to_dicts():
            values = [row['team'], row['games'], row['plays']]
            for m in MEASURES:
                value, rank = row[m], row[m + '_rank']
                values += ['—' if value is None else f'{value:+.3f}', '—' if rank is None else str(rank)]
            lines.append('| ' + ' | '.join(map(str, values)) + ' |')
        lines.append('')
    (output / f'epa_{season}_through_week_{through_week}.md').write_text('\n'.join(lines))
    return frame


if __name__ == '__main__':
    export(nfl.load_pbp([2026]), nfl.load_schedules([2026]))
