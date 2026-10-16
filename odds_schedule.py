"""Gate UTC GitHub cron slots by Pacific wall time, including DST."""
from datetime import datetime, timedelta, time, timezone
import os
import json
from pathlib import Path
from zoneinfo import ZoneInfo

PACIFIC=ZoneInfo('America/Los_Angeles')
LATEST_CRONS=('0 11,23 * * *','0 0,12 * * *')
LATEST_CRON=LATEST_CRONS[0]
OPENING_CRON='0 7,8 * * 0'


def opening_target(week):
    """The Sunday midnight Pacific before the NFL week's Tuesday start."""
    start=datetime.fromisoformat(week['start'].replace('Z','+00:00')).astimezone(ZoneInfo('America/New_York'))
    sunday=start.date()-timedelta(days=2)
    return datetime.combine(sunday,time(),PACIFIC).astimezone(timezone.utc)


def opening_window(target,observed):
    # Do not silently replace the fixed opening with a substantially later quote.
    return target<=observed<=target+timedelta(minutes=15)


def due_mode(now,event_name='schedule',cron=LATEST_CRON,last_fetched_at=None):
    local=now.astimezone(PACIFIC)
    if event_name=='workflow_dispatch':
        return 'latest'
    offset=local.utcoffset().total_seconds()/3600
    if ((cron==LATEST_CRONS[0] and offset==-7) or (cron==LATEST_CRONS[1] and offset==-8)) and local.hour in (4,16):
        if last_fetched_at:
            previous=datetime.fromisoformat(last_fetched_at.replace('Z','+00:00')).astimezone(PACIFIC)
            if (previous.date(),previous.hour)==(local.date(),local.hour):
                return 'skip'
        return 'latest'
    if cron==OPENING_CRON and local.weekday()==6 and local.hour==0 and local.minute<15:
        return 'opening'
    return 'skip'


if __name__=='__main__':
    now=datetime.now(timezone.utc)
    root=Path(__file__).resolve().parent
    snapshot_path=root/'reports/odds_2026.json'
    snapshot=json.loads(snapshot_path.read_text()) if snapshot_path.exists() else {}
    mode=due_mode(now,os.environ.get('EVENT_NAME','schedule'),os.environ.get('CRON_SCHEDULE',LATEST_CRON),snapshot.get('fetched_at'))
    schedule=json.loads((root/'reports/schedule_2026.json').read_text())
    if os.environ.get('EVENT_NAME')!='workflow_dispatch':
        first=min(opening_target(w) for w in schedule['weeks'])
        end=max(datetime.fromisoformat(w['end'].replace('Z','+00:00')) for w in schedule['weeks'])
        if not first<=now<end:
            mode='skip'
    print(f'Pacific clock: {now.astimezone(PACIFIC).isoformat(timespec="seconds")}; action: {mode}')
    output=os.environ.get('GITHUB_OUTPUT')
    if output:
        with open(output,'a') as stream:
            stream.write(f'run={str(mode!="skip").lower()}\nmode={mode}\n')
