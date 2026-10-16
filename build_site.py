"""Build the standalone HTML site from the checked-in EPA snapshot."""
import csv
import base64
import hashlib
import json
from pathlib import Path
from odds_schedule import opening_target

ROOT = Path(__file__).resolve().parent


def build():
    with (ROOT / 'reports/epa_2026_through_week_5.csv').open() as source:
        rows = list(csv.DictReader(source))
    for row in rows:
        for key, value in row.items():
            if key not in ('team', 'dimension', 'label'):
                row[key] = float(value) if value else None
    for row in rows:
        row['epa_per_100_plays'] = row['epa_per_play'] * 100 if row['epa_per_play'] is not None else None
        row['epa_per_100_plays_rank'] = row['epa_per_play_rank']
    if len(rows) != 256 or len({r['team'] for r in rows}) != 32:
        raise ValueError('Expected 32 teams across eight dimensions')
    note = (ROOT / 'reports/epa_2026_through_week_5.md').read_text().splitlines()[2]
    logo_root = ROOT / 'web/assets/logos'
    manifest = json.loads((logo_root / 'sources.json').read_text())
    logos = {}
    for team in sorted({r['team'] for r in rows}):
        image = (logo_root / f'{team}.png').read_bytes()
        if hashlib.sha256(image).hexdigest() != manifest['logos'][team]['sha256']:
            raise ValueError(f'Logo checksum mismatch: {team}')
        logos[team] = 'data:image/png;base64,' + base64.b64encode(image).decode('ascii')
    schedule = json.loads((ROOT / 'reports/schedule_2026.json').read_text())
    for week in schedule['weeks']:
        week['opening_target_at'] = opening_target(week).isoformat()
    schedule_teams = {g[side] for g in schedule['games'] for side in ('away_team', 'home_team')}
    if not schedule_teams.issubset(logos):
        raise ValueError('Missing logos for scheduled teams')
    odds_path = ROOT / 'reports/odds_2026.json'
    odds = json.loads(odds_path.read_text()) if odds_path.exists() else None
    payload = json.dumps({'odds': odds, 'rows': rows, 'source': note, 'logos': logos, 'schedule': schedule}, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c')
    template = (ROOT / 'web/index.template.html').read_text()
    output = ROOT / 'docs/index.html'
    output.parent.mkdir(exist_ok=True)
    output.write_text(template.replace('__EPA_DATA__', payload))
    print(f'Built {output.relative_to(ROOT)} ({output.stat().st_size:,} bytes)')


if __name__ == '__main__':
    build()
