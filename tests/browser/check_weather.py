"""Weather UI checks: real unavailable snapshot plus browser-only forecast fixtures."""
import functools,threading,shutil
from datetime import datetime,timezone
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(ROOT/'docs')))
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox','--disable-dev-shm-usage'])
    page=b.new_page(viewport={'width':1440,'height':1300},timezone_id='America/Los_Angeles')
    page.clock.install(time=datetime(2026,10,16,21,tzinfo=timezone.utc))
    errors=[];external=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:external.append(r.url) if r.url.startswith('https://') else None)
    page.goto(f'http://127.0.0.1:{server.server_port}/')
    assert page.locator('.kickoff-weather').count()==14
    assert 'No saved pregame forecast' in page.locator('[data-game="2026_06_SEA_DEN"] .kickoff-weather').text_content()
    assert 'outside forecast' not in page.locator('[data-game="2026_06_HOU_JAX"] .kickoff-weather').text_content()
    # Synthetic fixtures stay only in this browser, never the exported report or screenshots.
    page.evaluate('''() => {
      const entry=DATA.weather.games['2026_06_HOU_JAX'];entry.status='available';entry.forecast={
        conditions:'Light rain',temperature_f:55,feels_like_f:50,wind_mph:12,gust_mph:20,
        wind_direction_degrees:270,precipitation_probability:65,precipitation_inches:.04,
        retrieved_at:'2026-10-16T19:00:00Z',forecast_time:'2026-10-18T13:00:00Z'};
      renderMatchups();
    }''')
    weather=page.locator('[data-game="2026_06_HOU_JAX"] .kickoff-weather')
    assert '55°F' in weather.locator('summary').inner_text()
    weather.locator('summary').click()
    assert 'Retrieved' in weather.inner_text()
    for value in ['55°F','50°F','Wind W 12 mph','Gusts 20 mph','65%','0.04 in','Retrieved']:
        assert value in weather.text_content()
    page.evaluate("DATA.weather.games['2026_06_HOU_JAX'].status='stale_forecast';renderMatchups()")
    assert 'older forecast' in weather.text_content()
    # Enclosed/covered stadiums must not imply outside weather equals field conditions.
    sofi=page.locator('[data-game="2026_06_ARI_LA"] .kickoff-weather')
    assert 'Outside weather at kickoff' in sofi.text_content()
    assert 'Covered field, open sides' in sofi.text_content()
    page.locator('#week-selector').select_option('REG-18')
    assert '16-day window' in page.locator('.kickoff-weather').first.text_content()
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors and not external
    b.close()
server.shutdown()
print('PASS: weather states, Fahrenheit/mph/inches, direction, timestamps, stale forecast, covered venue, forecast horizon, mobile, no browser API requests')
