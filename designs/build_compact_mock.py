"""Build the compact possession-table mock without modifying the product."""
import base64
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rows = list(csv.DictReader((ROOT/'reports/epa_2026_through_week_5.csv').open()))
for row in rows:
    for key in row:
        if key not in ['team','dimension','label']:
            row[key] = float(row[key]) if row[key] else None
schedule = json.loads((ROOT/'reports/schedule_2026.json').read_text())
games = [g for g in schedule['games'] if g['week_key'] == 'REG-6']
teams = sorted({g[side] for g in games for side in ['away_team','home_team']})
logos = {team: 'data:image/png;base64,' + base64.b64encode((ROOT/f'web/assets/logos/{team}.png').read_bytes()).decode()
         for team in teams}
data = json.dumps(dict(rows=rows,games=games,logos=logos),allow_nan=False).replace('<','\\u003c')
template = (ROOT/'designs/compact.template.html').read_text()
(ROOT/'designs/compact-matchup-mock.html').write_text(template.replace('__COMPACT_DATA__',data))
print('Built compact Week 6 mock with',len(games),'games. Product unchanged.')
