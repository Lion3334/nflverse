"""Optional real-browser checks: pip install playwright; requires Chromium."""
import csv
import io
import json
import shutil
import functools
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT / 'docs')))
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}/'
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=shutil.which('chromium'), headless=True,
                                args=['--no-sandbox', '--disable-dev-shm-usage'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1100}, device_scale_factor=1)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(url)
    page.locator('[data-view="leaderboards"]').click()
    assert page.locator('[data-metric="epa_per_100_plays"]').get_attribute('aria-pressed') == 'true'
    assert page.locator('.team-icon').count() == 32
    assert page.locator('.point image').count() == 32
    page.evaluate('''async () => {
        const images = [...document.querySelectorAll('.team-icon')];
        await Promise.all(images.map(image => image.decode()));
        for (const image of images) {
            if (!image.src.startsWith('data:image/png;base64,') || !image.naturalWidth) throw new Error('Missing bundled logo');
        }
        await Promise.all([...document.querySelectorAll('.point image')].map(async el => {
            const image = new Image(); image.src = el.getAttribute('href'); await image.decode();
        }));
    }''')
    data = json.loads(page.locator('#epa-data').text_content())['rows']
    for dimension in dict.fromkeys(r['dimension'] for r in data):
        page.locator(f'[data-dimension="{dimension}"]').click()
        for metric in ['total_epa', 'epa_per_100_plays', 'epa_per_game']:
            page.locator(f'[data-metric="{metric}"]').click()
            assert page.locator('#rows tr').count() == 32
            assert page.locator('.point').count() == 32
            points = page.locator('.point').evaluate_all('(els)=>els.map(e=>({team:e.dataset.team,x:+e.dataset.x,v:+e.dataset.value}))')
            values = [v['v'] for v in points]
            lower = dimension.startswith('def') or dimension == 'st_opponent'
            assert values == sorted(values, reverse=not lower)
            assert all(a['x'] >= b['x'] for a,b in zip(points, points[1:]))
            assert page.locator('.endlabel').all_text_contents() == ['WORST', 'BEST']
            # Every dot uses one linear scale: value differences map exactly to x differences.
            slope = (points[-1]['x'] - points[0]['x']) / (points[-1]['v'] - points[0]['v'])
            for point in points:
                assert abs(point['x'] - points[0]['x'] - slope * (point['v'] - points[0]['v'])) < 1e-7
            expected = min((r for r in data if r['dimension'] == dimension), key=lambda r:r[metric] if lower else -r[metric])
            assert points[0]['team'] == expected['team']
            first_row = page.locator('#rows tr').first
            assert first_row.locator('td').first.text_content() == '1'
            # Labels don't obscure each other.
            boxes = page.locator('.point rect').evaluate_all('(els)=>els.map(e=>{const b=e.getBoundingClientRect();return {x:b.x,y:b.y,w:b.width,h:b.height}})')
            for i, a in enumerate(boxes):
                for b in boxes[i+1:]:
                    assert not (a['x'] < b['x']+b['w'] and a['x']+a['w'] > b['x'] and a['y'] < b['y']+b['h'] and a['y']+a['h'] > b['y'])
    page.locator('[data-dimension="off_total"]').click()
    page.locator('[data-metric="epa_per_100_plays"]').click()
    page.locator('.point').first.click()
    assert 'Buffalo Bills' in page.locator('#selection').text_content()
    assert page.locator('#rows tr.selected').count() == 1
    page.locator('#rows tr').nth(2).locator('button').focus()
    page.keyboard.press('Enter')
    assert page.locator('#rows tr').nth(2).get_attribute('class') == 'selected'
    with page.expect_download() as download:
        page.locator('#download').click()
    downloaded = download.value
    rows = list(csv.DictReader(io.StringIO(Path(downloaded.path()).read_text())))
    assert len(rows) == 32 and rows[0]['team'] == 'BUF'
    assert 'epa_per_100_plays' in rows[0] and 'epa_per_play' not in rows[0]
    assert abs(float(rows[0]['epa_per_100_plays']) - 100 * next(r['epa_per_play'] for r in data if r['team']=='BUF' and r['dimension']=='off_total')) < 1e-10
    page.reload()
    assert page.locator('[data-dimension="off_total"]').get_attribute('aria-selected') == 'true'
    page.locator('[data-dimension="off_total"]').focus()
    page.keyboard.press('ArrowRight')
    assert page.locator('[data-dimension="def_pass"]').get_attribute('aria-selected') == 'true'
    page.goto(url + '#dimension=off_total&metric=epa_per_100_plays')
    page.evaluate('document.activeElement.blur()')
    page.locator('.team-icon').evaluate_all('(els)=>Promise.all(els.map(e=>e.decode()))')
    page.screenshot(path='/tmp/nfl-epa-desktop.png', full_page=False)
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    assert page.locator('.point').count() == 32
    page.screenshot(path='/tmp/nfl-epa-mobile.png', full_page=True)
    page.goto(url + '#dimension=off_pass&metric=epa_per_play')
    assert page.locator('[data-metric="epa_per_100_plays"]').get_attribute('aria-pressed') == 'true'
    assert not errors, errors
    browser.close()
server.shutdown()
print('PASS: all 24 dimension/metric views, exact linear positioning, no label collisions, table selection, keyboard controls, CSV, URL state, mobile layout, all 32 bundled logos decode in table and plot; no browser errors')
