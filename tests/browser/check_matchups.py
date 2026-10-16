"""Exercise season schedule, visitor date/timezone selection and navigation."""
import functools
import json
import shutil
import threading
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT/'docs')))
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}/'
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=shutil.which('chromium'), args=['--no-sandbox','--disable-dev-shm-usage'])
    context = browser.new_context(viewport={'width':1440,'height':1100}, timezone_id='America/Los_Angeles')
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.clock.install(time=datetime(2026,10,16,19,tzinfo=timezone.utc))
    page.goto(url)
    assert page.locator('#matchups-view').is_visible()
    assert not page.locator('#epa-view').is_visible()
    assert page.locator('#week-selector').input_value() == 'REG-6'
    assert page.locator('#current-week-badge').is_visible()
    assert page.locator('#week-selector option').count() == 18
    data = json.loads(page.locator('#epa-data').text_content())['schedule']
    all_ids = []
    for week in data['weeks']:
        page.locator('#week-selector').select_option(week['key'])
        cards = page.locator('.game-card')
        expected = [g for g in data['games'] if g['week_key'] == week['key']]
        assert cards.count() == len(expected)
        actual = cards.evaluate_all('(els)=>els.map(e=>({id:e.dataset.game,time:e.dataset.kickoff}))')
        all_ids += [a['id'] for a in actual]
        times = [a['time'] for a in actual if a['time']]
        assert times == sorted(times)
        assert {a['id'] for a in actual} == {g['game_id'] for g in expected}
        assert page.locator('.matchup-logo').count() == 2*len(expected)
    assert len(all_ids) == len(set(all_ids)) == 272
    # Boundary policy, including the November DST change.
    for index, week in enumerate(data['weeks']):
        start = datetime.fromisoformat(week['start'])
        page.clock.set_system_time(start-timedelta(minutes=1))
        page.goto(url)
        assert page.locator('#week-selector').input_value() == data['weeks'][max(0,index-1)]['key']
        page.clock.set_system_time(start)
        page.goto(url)
        assert page.locator('#week-selector').input_value() == week['key']
    page.clock.set_system_time(datetime(2027,3,1,tzinfo=timezone.utc))
    page.goto(url)
    assert page.locator('#week-selector').input_value() == 'REG-18'
    assert not page.locator('#current-week-badge').is_visible()
    # Explicit week links override current date and survive reload.
    page.clock.set_system_time(datetime(2026,10,16,19,tzinfo=timezone.utc))
    page.goto(url+'#view=matchups&week=REG-2')
    assert page.locator('#week-selector').input_value() == 'REG-2'
    page.reload()
    assert page.locator('#week-selector').input_value() == 'REG-2'
    page.locator('#next-week').click()
    assert page.locator('#week-selector').input_value() == 'REG-3'
    page.locator('#prev-week').click()
    assert page.locator('#week-selector').input_value() == 'REG-2'
    page.locator('#current-week').click()
    assert page.locator('#week-selector').input_value() == 'REG-6'
    # Compare the displayed kickoff with the browser's local-time formatter.
    first = page.locator('.game-card').first
    instant = first.get_attribute('data-kickoff')
    expected = page.evaluate("v=>new Intl.DateTimeFormat(undefined,{hour:'numeric',minute:'2-digit',timeZoneName:'short'}).format(new Date(v))",instant)
    assert first.locator('time').text_content() == expected
    assert 'America/Los_Angeles' in page.locator('#schedule-context').text_content()
    # Original leaderboard deep links still work.
    page.goto(url+'#dimension=def_pass&metric=epa_per_game')
    assert page.locator('#epa-view').is_visible()
    assert page.locator('[data-metric="epa_per_game"]').get_attribute('aria-pressed') == 'true'
    page.locator('[data-view="matchups"]').click()
    page.locator('.matchup-logo').evaluate_all('(els)=>Promise.all(els.map(e=>e.decode()))')
    page.evaluate('document.activeElement.blur()')
    page.screenshot(path='/tmp/nfl-matchups-desktop.png')
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path='/tmp/nfl-matchups-mobile.png',full_page=True)
    # A visitor in a different timezone still gets the same NFL week, with local kickoff times.
    tokyo = browser.new_context(timezone_id='Asia/Tokyo')
    other = tokyo.new_page()
    other.clock.install(time=datetime(2026,10,16,19,tzinfo=timezone.utc))
    other.goto(url)
    assert other.locator('#week-selector').input_value() == 'REG-6'
    assert 'Asia/Tokyo' in other.locator('#schedule-context').text_content()
    assert other.locator('.game-card').first.locator('time').text_content() != expected
    assert not errors, errors
    browser.close()
server.shutdown()
print('PASS: all 272 games/18 weeks, chronological kickoffs, date boundaries/DST, date-selected Week 6, preseason/postseason bounds, share links, navigation, timezones, mobile, and leaderboard links')
