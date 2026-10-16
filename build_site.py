"""Build the standalone HTML site from the checked-in EPA snapshot."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build():
    with (ROOT / 'reports/epa_2026_through_week_5.csv').open() as source:
        rows = list(csv.DictReader(source))
    for row in rows:
        for key, value in row.items():
            if key not in ('team', 'dimension', 'label'):
                row[key] = float(value) if value else None
    if len(rows) != 256 or len({r['team'] for r in rows}) != 32:
        raise ValueError('Expected 32 teams across eight dimensions')
    note = (ROOT / 'reports/epa_2026_through_week_5.md').read_text().splitlines()[2]
    payload = json.dumps({'rows': rows, 'source': note}, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c')
    template = (ROOT / 'web/index.template.html').read_text()
    output = ROOT / 'docs/index.html'
    output.parent.mkdir(exist_ok=True)
    output.write_text(template.replace('__EPA_DATA__', payload))
    print(f'Built {output.relative_to(ROOT)} ({output.stat().st_size:,} bytes)')


if __name__ == '__main__':
    build()
