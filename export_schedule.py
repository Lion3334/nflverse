"""Refresh the published 2026 schedule snapshot; rebuild the HTML afterwards."""
import json
from datetime import datetime, timezone
from pathlib import Path

from schedule_data import schedule_payload


def export():
    import nflreadpy as nfl
    payload = schedule_payload(nfl.load_schedules([2026]).to_dicts())
    payload['retrieved_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    output = Path(__file__).resolve().parent / 'reports/schedule_2026.json'
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    print(f'Exported {len(payload["games"])} games in {len(payload["weeks"])} weeks')


if __name__ == '__main__':
    export()
