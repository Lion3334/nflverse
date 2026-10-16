"""Verify real unavailable states and synthetic quote rendering without API calls."""
import functools
import shutil
import threading
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(ROOT/'docs')))
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':1440,'height':1100})
    page.clock.install(time=datetime(2026,10,16,19,tzinfo=timezone.utc))
    errors=[];external=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:external.append(r.url) if r.url.startswith('https://') else None)
    page.goto(f'http://127.0.0.1:{server.server_port}/')
    assert page.locator('.odds-panel').count()==14
    assert page.locator('.odds-market').count()==28
    # Check the real empty snapshot against what the API actually returned.
    assert '0 spread and 0 total quotes' in page.locator('#odds-coverage').text_content()
    assert page.locator('.odds-unavailable').count()==28
    # Test fixtures only, injected into this browser; never written to reports or the site.
    page.evaluate('''() => {
      const first={home_point:-3.5,away_point:3.5,observed_at:'2026-10-15T00:00:00Z',source_updated_at:'2026-10-14T23:59:00Z'};
      const last={...first,home_point:-4.5,away_point:4.5};
      DATA.odds.games['2026_06_SEA_DEN']={
        spreads:{first_observed:first,latest:last,returned_at_last_check:true},
        totals:{first_observed:{...first,point:44.5},latest:{...last,point:45.5},returned_at_last_check:false}
      };renderMatchups();
    }''')
    card=page.locator('[data-game="2026_06_SEA_DEN"]')
    spread=card.locator('[data-market="spreads"]')
    assert 'DEN −3.5' in spread.text_content() and 'DEN −4.5' in spread.text_content()
    total=card.locator('[data-market="totals"]')
    assert 'O/U 44.5' in total.text_content() and 'O/U 45.5' in total.text_content()
    assert total.locator('.odds-stale').is_visible()
    assert spread.locator('.odds-stale').count()==0
    page.evaluate("DATA.odds.games['2026_06_SEA_DEN'].spreads.latest.home_point=2.5;renderMatchups()")
    assert 'SEA −2.5' in card.text_content()
    page.evaluate("DATA.odds.games['2026_06_SEA_DEN'].spreads.latest.home_point=0;renderMatchups()")
    assert 'Pick’em' in card.text_content()
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors and not external
    browser.close()
server.shutdown()
print('PASS: unavailable real snapshot, first/latest spread and total, favorite signs, pick’em, stale quotes, mobile; no browser API requests')
