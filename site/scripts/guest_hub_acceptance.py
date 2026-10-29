#!/usr/bin/env python3
"""Headless guest-hub checks. No company profile, submissions or production changes."""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
REPORT = Path(os.environ.get('BRAVIS_HUB_REPORT_DIR', ROOT / 'browser-report/guest-hub'))
REPORT.mkdir(parents=True, exist_ok=True)
LOONA = 'https://app.loona.ai/4992/create/register?source=qr&tag=none'
ALL = {'guest_card', 'lunch', 'menu_evening', 'corporate', 'future_booking', 'public_review', 'private_feedback'}
checks = []
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
base = f'http://127.0.0.1:{port}'
server = subprocess.Popen([sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1', '--directory', str(ROOT / 'dist')],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
original = (ROOT / 'dist/go/index.html').read_text(encoding='utf-8')
settings = json.loads((ROOT / 'content/guest-hub.json').read_text())
assert settings['holidayOverrides']['2026-11-04']['state'] == 'unconfirmed'
requests = []

def freeze(page, iso):
    millis = int(datetime.fromisoformat(iso).timestamp() * 1000)
    page.add_init_script(f"""const OriginalDate = Date; const fixedTime = {millis};
    globalThis.Date = class extends OriginalDate {{
      constructor(...args) {{ super(...(args.length ? args : [fixedTime])); }}
      static now() {{ return fixedTime; }}
    }};""")

def order(page):
    return page.locator('[data-hub-id]').evaluate_all('(items) => items.map(item => item.dataset.hubId)')

def context(browser, *, width=390, js=True, iso='2026-11-02T09:00:00+00:00', body=None, fail_clock=False):
    ctx = browser.new_context(viewport={'width': width, 'height': 844}, java_script_enabled=js,
                              timezone_id='America/Los_Angeles')
    def route(req):
        request = req.request
        requests.append({'method': request.method, 'url': request.url})
        if not request.url.startswith(base + '/'):
            req.abort()
        elif body is not None and request.url.split('?', 1)[0] == base + '/go/':
            req.fulfill(status=200, content_type='text/html; charset=utf-8', body=body)
        else:
            req.continue_()
    ctx.route('**/*', route)
    page = ctx.new_page()
    if js:
        freeze(page, iso)
        if fail_clock:
            page.add_init_script("Intl.DateTimeFormat = function () { throw new Error('Clock unavailable'); };")
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(base + '/go/', wait_until='networkidle')
    assert not errors, errors
    return ctx, page

try:
    with sync_playwright() as pw:
        executable = os.environ.get('BRAVIS_CHROMIUM_EXECUTABLE') or shutil.which('chromium')
        browser = pw.chromium.launch(executable_path=executable, headless=True,
                                     args=['--no-sandbox', '--disable-dev-shm-usage'])
        for width in [1440, 390, 320]:
            ctx, page = context(browser, width=width)
            expect(page.locator('h1')).to_have_text('Меню и карта гостя')
            assert set(order(page)) == ALL
            expect(page.locator('[data-promo-variant="lunch"]')).to_be_visible()
            expect(page.locator('[data-promo-variant="evening"]')).to_be_hidden()
            expect(page.locator('[data-promo-variant="lunch"]')).to_contain_text('690 ₽')
            expect(page.locator('[data-promo-variant="lunch"]')).to_have_attribute('href', '/lunch/')
            image = page.locator('[data-promo-variant="lunch"] img')
            image.evaluate('(image) => image.decode()')
            assert image.evaluate('(image) => image.naturalWidth > 0')
            assert order(page)[:2] == ['guest_card', 'lunch']
            expect(page.locator('[data-hub-id="guest_card"] a')).to_have_attribute('href', LOONA)
            assert page.locator('[data-hub-id] a').count() == 7
            expect(page.locator('[data-hub-id="guest_card"] a')).to_have_attribute('data-track', 'loona_signup_click')
            assert page.locator('[data-hub-id] .guest-hub-card__arrow svg').count() == 7
            menu = page.locator('.guest-hub-menu')
            expect(menu).to_have_attribute('href', '/menu/')
            assert menu.bounding_box()['height'] >= 44
            if width <= 960:
                assert page.locator('.guest-hub-header').evaluate('(e)=>getComputedStyle(e).position') == 'sticky'
                page.emulate_media(reduced_motion='reduce')
                page.evaluate('scrollTo(0,document.body.scrollHeight)')
                expect(page.locator('.back-to-top')).to_be_visible()
                assert page.locator('.guest-hub-header').bounding_box()['y'] >= -1
                assert page.locator('.guest-hub-menu').bounding_box()['y'] < 100
                page.locator('.back-to-top').click()
                page.wait_for_function('scrollY < 2')
                expect(page.locator('.guest-hub-brand')).to_be_focused()
                expect(page.locator('.back-to-top')).to_be_hidden()
            assert page.locator('form,input,textarea,iframe').count() == 0
            assert page.locator('.mobile-bottom-cta,.site-header').count() == 0
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
            for link in page.locator('[data-hub-id] a').all():
                assert link.bounding_box()['height'] >= 44
            # The existing consent banner does not block the first action.
            card = page.locator('[data-hub-id="guest_card"] a').bounding_box()
            banner = page.locator('.cookie-banner').bounding_box()
            assert card['y'] + card['height'] <= banner['y'] if banner else True
            page.screenshot(path=str(REPORT / f'guest-hub-{width}.png'), full_page=True)
            ctx.close()
            checks.append(f'Layout, links, no forms, primary action and consent at {width}px')
        ctx, page = context(browser, width=320, js=False)
        assert len(order(page)) == 7 and order(page)[0] == 'guest_card'
        expect(page.locator('[data-lunch-badge]')).to_be_hidden()
        expect(page.locator('[data-promo-variant="evening"]')).to_be_visible()
        expect(page.locator('[data-promo-variant="evening"]')).to_contain_text('Соберитесь своей компанией')
        expect(page.locator('[data-promo-variant="evening"]')).to_have_attribute('href', '/banquets/')
        expect(page.locator('[data-promo-variant="lunch"]')).to_be_hidden()
        expect(page.locator('[data-lunch-note]')).to_contain_text('праздничные')
        assert page.locator('[data-hub-id] a').count() == 7
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
        page.screenshot(path=str(REPORT / 'guest-hub-nojs-320.png'), full_page=True)
        ctx.close()
        checks.append('Seven real links, holiday note and no overflow without JavaScript')
        cases = [
            ('2026-11-02T07:59:59+00:00', 'regular', 'menu_evening'),
            ('2026-11-02T08:00:00+00:00', 'open', 'lunch'),
            ('2026-11-02T12:59:59+00:00', 'open', 'lunch'),
            ('2026-11-02T13:00:00+00:00', 'regular', 'menu_evening'),
            ('2026-11-07T09:00:00+00:00', 'regular', 'menu_evening'),
            ('2026-11-04T09:00:00+00:00', 'unconfirmed', 'menu_evening'),
            ('2026-11-05T09:00:00+00:00', 'open', 'lunch'),
        ]
        for iso, state, second in cases:
            ctx, page = context(browser, iso=iso)
            expect(page.locator('[data-guest-hub]')).to_have_attribute('data-lunch-state', state)
            assert order(page)[0] == 'guest_card' and order(page)[1] == second
            assert set(order(page)) == ALL
            promo_key = 'lunch' if state == 'open' else 'evening'
            expect(page.locator('[data-promo-variant="' + promo_key + '"]')).to_be_visible()
            assert page.locator('[data-promo-variant]:visible').count() == 1
            if state == 'unconfirmed':
                expect(page.locator('[data-lunch-note]')).to_contain_text('уточните')
                expect(page.locator('[data-lunch-badge]')).to_be_hidden()
            ctx.close()
            checks.append(f'Moscow time {iso}: {state}; every link retained')
        marker = '"state": "unconfirmed"'
        for override, state in [
            ('"state": "no_lunch_confirmed"', 'no-lunch'),
            ('"state": "regular_lunch_confirmed"', 'open'),
            ('"state": "special_hours_confirmed", "start": "12:00", "end": "15:00"', 'open-special'),
        ]:
            assert marker in original
            ctx, page = context(browser, iso='2026-11-04T09:00:00+00:00', body=original.replace(marker, override))
            expect(page.locator('[data-guest-hub]')).to_have_attribute('data-lunch-state', state)
            assert set(order(page)) == ALL
            ctx.close()
            checks.append('Manual holiday override: ' + state)
        ctx, page = context(browser, fail_clock=True)
        assert order(page)[:2] == ['guest_card', 'lunch']
        assert page.locator('[data-guest-hub]').get_attribute('data-lunch-state') is None
        expect(page.locator('[data-lunch-badge]')).to_be_hidden()
        ctx.close()
        checks.append('Clock/Intl failure keeps static links and conservative note')
        sys.path.insert(0, str(ROOT / 'src'))
        from guest_hub import render_guest_hub
        head = re.sub(r'<link rel="stylesheet" href="/assets/guest-hub\.css(?:\?v=[a-f0-9]+)?">', '', original.split('<a class="skip"')[0])
        config = json.loads((ROOT / 'site.config.json').read_text())
        disabled = render_guest_hub(config, {**settings, 'loonaEnabled': False}, head, 690, 'https://reservation.yandex.ru/partner-reserve/forms/' + config['smartReserveId'])
        ctx, page = context(browser, body=disabled)
        assert page.locator('[data-hub-id] a').count() == 6
        expect(page.locator('[data-hub-id="guest_card"]')).to_contain_text('временно недоступно')
        expect(page.locator('[data-hub-id="public_review"] a')).to_be_visible()
        assert page.locator('form,input,textarea').count() == 0
        ctx.close()
        checks.append('Optional Loona outage does not disable menu, reviews or future visits')
        for consent in ['no', 'yes']:
            ctx, page = context(browser)
            page.locator('[data-consent="' + consent + '"]').click()
            assert page.evaluate("localStorage.getItem('bravis_analytics_consent_v1')") == consent
            page.reload(wait_until='networkidle')
            assert page.locator('.cookie-banner').count() == 0
            assert page.locator('[data-hub-id] a').count() == 7
            page.evaluate('window.testGoals=[];window.ym=(...args)=>window.testGoals.push(args);')
            link = page.locator('[data-hub-id="future_booking"] a')
            link.evaluate("(a)=>a.addEventListener('click',event=>event.preventDefault())")
            link.click()
            goals = page.evaluate('window.testGoals')
            assert any('reserve_click' in goal for goal in goals) == (consent == 'yes')
            assert page.locator('[data-hub-id="public_review"] a').count() == 1
            ctx.close()
            checks.append('Existing consent persisted; reserve goal gated by ' + consent)
        ctx, page = context(browser, width=320)
        page.locator('[data-consent="no"]').click()
        page.locator('[data-hub-id="guest_card"] a').focus()
        page.keyboard.press('Tab')
        page.keyboard.press('Shift+Tab')
        expect(page.locator('[data-hub-id="guest_card"] a')).to_be_focused()
        assert page.locator('[data-hub-id="guest_card"] a').evaluate("(a)=>getComputedStyle(a).outlineStyle") != 'none'
        page.keyboard.press('Tab')
        expect(page.locator('[data-hub-id="lunch"] a')).to_be_focused()
        page.locator('body').evaluate("(e)=>e.style.fontSize='200%'")
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
        ctx.close()
        checks.append('DOM/keyboard order, visible focus and larger base text at 320px')
        ctx, page = context(browser)
        page.goto(base + '/go/?phone=PRIVATE_TEST&email=PRIVATE_TEST&redirect=https://invalid.example/', wait_until='networkidle')
        assert page.url == base + '/go/', 'Untrusted URL was not cleared before analytics'
        assert 'PRIVATE_TEST' not in page.locator('body').inner_text()
        assert all('PRIVATE_TEST' not in (a.get_attribute('href') or '') for a in page.locator('a').all())
        page.evaluate("localStorage.setItem('bravis_analytics_consent_v1','yes')")
        page.goto(base + '/go/?phone=PRIVATE_TEST#PRIVATE_TEST', wait_until='networkidle')
        assert page.url == base + '/go/'
        assert page.evaluate("localStorage.getItem('bravis_analytics_consent_v1')") == 'yes'
        assert page.evaluate("window.BRAVIS_ANALYTICS.ymId") == '113768615'
        page.add_init_script("history.replaceState = () => { throw new Error('History unavailable'); };")
        page.goto(base + '/go/?phone=PRIVATE_TEST', wait_until='networkidle')
        assert page.evaluate("Object.keys(window.BRAVIS_ANALYTICS).length") == 0
        assert page.evaluate("localStorage.getItem('bravis_analytics_consent_v1')") == 'yes'
        assert page.locator('[data-hub-id] a').count() == 7
        ctx.close()
        checks.append('Untrusted URL cleared before opted-in analytics; saved consent unchanged')
        checks.append('Blocked history cleanup disables only analytics, not guest links or saved consent')
        assert all(req['method'] == 'GET' for req in requests), 'Unexpected mutating request'
        assert not any('5047' in req['url'] for req in requests)
        assert not any('app.loona.ai' in req['url'] for req in requests), 'Loona loaded before explicit guest action'
        checks.append('Only GET requests; no proactive Loona/checkout request')
        browser.close()
    report = {'status': 'PASS', 'checks': checks, 'count': len(checks),
              'screenshots': [p.name for p in sorted(REPORT.glob('*.png'))],
              'all_requests_get': True, 'company_browser_used': False,
              'external_requests_aborted': True, 'submissions_or_payments': False}
    (REPORT / 'acceptance.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
finally:
    server.terminate()
    server.wait(timeout=5)

