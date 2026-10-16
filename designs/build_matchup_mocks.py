"""Build a separate design study; never writes product files."""
import base64
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rows = list(csv.DictReader((ROOT / 'reports/epa_2026_through_week_5.csv').open()))
for r in rows:
    for k in r:
        if k not in ['team', 'dimension', 'label']:
            r[k] = float(r[k]) if r[k] else None
logos = {team: 'data:image/png;base64,' + base64.b64encode((ROOT / f'web/assets/logos/{team}.png').read_bytes()).decode()
         for team in ['SEA','DEN']}
payload=json.dumps(dict(rows=rows,logos=logos),allow_nan=False).replace('<','\\u003c')
source=(ROOT/'designs/matchup.template.html').read_text()
(ROOT/'designs/epa-matchup-mocks.html').write_text(source.replace('__MOCK_DATA__',payload))
print('Built designs/epa-matchup-mocks.html; product files unchanged')
