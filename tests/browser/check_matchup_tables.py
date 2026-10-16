"""Check the primary three-table matchups and per-100 conversion with real data."""
import functools
import threading
import shutil
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(ROOT/'docs')))
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox','--disable-dev-shm-usage'])
    page=b.new_page(viewport={'width':1440,'height':1300},timezone_id='America/Los_Angeles')
    page.clock.install(time=datetime(2026,10,16,19,tzinfo=timezone.utc))
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{server.server_port}/')
    assert page.locator('[data-matchup-metric="epa_per_100_plays"]').get_attribute('aria-pressed')=='true'
    assert page.locator('.game-card').count()==14
    assert page.locator('.unit-table').count()==42
    assert page.locator('.unit-table td').count()==224
    for measure in ['total_epa','epa_per_game','epa_per_100_plays']:
        page.locator(f'[data-matchup-metric="{measure}"]').click()
        assert page.evaluate('''m=>[...document.querySelectorAll('.unit-table td')].every(cell=>{
          const r=DATA.rows.find(r=>r.team===cell.dataset.epaTeam&&r.dimension===cell.dataset.epaDimension);
          return +cell.dataset.epaValue===r[m]&&+cell.dataset.rank===r[m+'_rank']&&cell.querySelector('.unit-value').textContent===fmt(r[m],m)&&cell.querySelector('.unit-rank').textContent==='#'+r[m+'_rank']&&cell.style.background.replaceAll(' ','')===heatColor(r[m+'_rank']).replaceAll(' ','');
        })''',measure)
    assert page.evaluate('DATA.rows.every(r=>r.epa_per_100_plays === 100*r.epa_per_play && r.epa_per_100_plays_rank===r.epa_per_play_rank)')
    # Six scrimmage cells in each possession, four special-teams cells.
    first=page.locator('.game-card').first
    assert first.locator('.possession').nth(0).locator('td').count()==6
    assert first.locator('.possession').nth(1).locator('td').count()==6
    assert first.locator('.special-teams td').count()==4
    assert first.locator('.odds-market').count()==2
    xs=first.locator('.possession').evaluate_all('(els)=>els.map(e=>e.getBoundingClientRect().x)')
    assert xs[0]<xs[1]<xs[2]
    # No hindsight: the saved Week 5 snapshot cannot be used as Week 1 pregame data.
    page.locator('#week-selector').select_option('REG-1')
    assert 'Unavailable' in page.locator('.unit-table').first.text_content()
    assert page.locator('.unit-table td[data-epa-value=""]').count()==16*16
    page.locator('#week-selector').select_option('REG-6')
    page.locator('[data-matchup-metric="total_epa"]').click()
    page.locator('[data-view="leaderboards"]').click()
    assert page.locator('[data-metric="total_epa"]').get_attribute('aria-pressed')=='true'
    page.locator('[data-metric="epa_per_100_plays"]').click()
    page.locator('[data-view="matchups"]').click()
    assert page.locator('[data-matchup-metric="epa_per_100_plays"]').get_attribute('aria-pressed')=='true'
    page.reload()
    assert page.locator('[data-matchup-metric="epa_per_100_plays"]').get_attribute('aria-pressed')=='true'
    page.locator('.matchup-logo').evaluate_all('(els)=>Promise.all(els.map(e=>e.decode()))')
    page.evaluate('document.activeElement.blur()')
    page.screenshot(path='/tmp/nfl-matchup-tables-desktop.png')
    first.screenshot(path='/tmp/nfl-matchup-tables-game.png')
    for width in [900,390]:
        page.set_viewport_size({'width':width,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path='/tmp/nfl-matchup-tables-mobile.png')
    # Future snapshot must advance new games without changing historical Week 6.
    page.evaluate("DATA.snapshots['6']=DATA.rows.map(r=>({...r,epa_per_100_plays:123}));DATA.epa.through_week=6;renderMatchups()")
    assert 'Through Week 5' in page.locator('#matchup-epa-context').inner_text()
    page.locator('#week-selector').select_option('REG-7')
    assert 'Through Week 6' in page.locator('#matchup-epa-context').inner_text()
    assert page.locator('.unit-table td[data-epa-value="123"]').count()>0
    page.locator('#week-selector').select_option('REG-6')
    assert page.locator('.unit-table td[data-epa-value="123"]').count()==0
    assert not errors,errors
    b.close()
server.shutdown()
print('PASS: 14 games, 42 tables, 224 correctly scaled/ranked/colored cells, shared metrics, historical guard, FanDuel, desktop/tablet/mobile')
