#!/usr/bin/env python3
"""BRAVIS automated browser acceptance: desktop/mobile, menu reader and nav.
Outputs three screenshots in site/browser-report without touching production servers.
"""
import contextlib
import socket
import subprocess
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'dist'
REPORT=ROOT/'browser-report'
REPORT.mkdir(exist_ok=True)
with socket.socket() as s:
    s.bind(('127.0.0.1',0))
    port=s.getsockname()[1]
server=subprocess.Popen(
    [sys.executable,'-m','http.server',str(port),'--bind','127.0.0.1','--directory',str(DIST)],
    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL
)
base=f'http://127.0.0.1:{port}'
def loaded(img):
    return img.evaluate('(e)=>e.complete && e.naturalWidth > 0')
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        desktop=browser.new_context(viewport={'width':1440,'height':900},device_scale_factor=1)
        page=desktop.new_page()
        page_errors=[]
        page.on('pageerror', lambda exc: page_errors.append(str(exc)))
        page.goto(base+'/',wait_until='networkidle',timeout=30000)
        expect(page.locator('h1')).to_contain_text('Вкус встреч')
        expect(page.locator('.hero-photo')).to_be_visible()
        # Official Yandex site-form integration: desktop header button points to exact restaurant.
        reserve='https://reservation.yandex.ru/partner-reserve/forms/5b1e469e-871a-4eb8-bd2a-787ec2d011c3'
        expect(page.locator('.header-actions a[href="'+reserve+'"]')).to_be_visible()
        assert page.locator('.header-actions a[href="'+reserve+'"]').get_attribute('target')=='_blank'
        assert loaded(page.locator('.hero-photo')),'Hero image failed to load'
        # Independently validate conversion points without sending any booking or data.
        expect(page.locator('.delivery-action')).to_have_attribute('href','https://eda.yandex.ru/r/bravis?placeSlug=bravis')
        expect(page.locator('.loyalty-action')).to_have_attribute('href','https://app.loona.ai/4992/create/register?source=qr&tag=none')
        assert page.locator('.delivery-action').get_attribute('target')=='_blank'
        assert page.locator('.loyalty-action').get_attribute('rel')=='noopener noreferrer'
        assert loaded(page.locator('.loyalty-qr img')),'Loona card enrollment QR did not load'
        assert page.locator('.loyalty-qr').get_attribute('href')==page.locator('.loyalty-action').get_attribute('href')
        expect(page.locator('#delivery')).to_be_visible()
        expect(page.locator('#loyalty')).to_be_visible()
        assert not page_errors,'JavaScript runtime errors on home: '+str(page_errors)
        assert page.locator('html').get_attribute('lang')=='ru'
        assert 'noindex' in page.locator('meta[name="robots"]').get_attribute('content')
        # Full-page screenshots may skip lazy-loading until photos are scrolled into view.
        # Test that real interior and event images load, then capture an accurate visual.
        for img in page.locator('.gallery-grid img, .events-photo img').all():
            img.scroll_into_view_if_needed()
            img.evaluate('(e) => e.decode()')
            assert loaded(img), 'Restaurant interior/gallery photo failed to load: '+str(img.get_attribute('src'))
        page.locator('h1').scroll_into_view_if_needed()
        page.screenshot(path=str(REPORT/'home-desktop.png'),full_page=True)
        print('PASS: desktop hero, real gallery and event photos, no broken lazy-loaded images')
        page.goto(base+'/menu/',wait_until='networkidle')
        expect(page.locator('.print-card')).to_have_count(5)
        # The owner rejected old dish thumbnails: printed menu covers are retained,
        # but each textual dish is intentionally shown without a food photograph.
        expect(page.locator('.menu-items .dish img')).to_have_count(0)
        assert page.locator('.menu-items .dish').count()>=60, 'Textual menu items missing'
        for i in range(5):
            thumb=page.locator('.print-card__image img').nth(i)
            thumb.scroll_into_view_if_needed()
            assert loaded(thumb),f'Menu cover {i+1} broken'
        page.locator('.print-card').first.click()
        dialog=page.locator('#menu-lightbox')
        expect(dialog).to_be_visible()
        expect(page.locator('#menu-lightbox-image')).to_be_visible()
        assert loaded(page.locator('#menu-lightbox-image')),'Menu full-screen image missing'
        assert 'menu-lightbox--single' in dialog.get_attribute('class'), 'Single-page menus should use the wider viewer'
        expect(page.locator('#menu-lightbox-prev')).to_be_hidden()
        expect(page.locator('#menu-lightbox-next')).to_be_hidden()
        page.locator('#menu-lightbox-close').click()
        expect(dialog).not_to_be_visible()
        page.screenshot(path=str(REPORT/'menu-desktop.png'),full_page=True)
        print('PASS: five actual menu thumbnails and full-screen viewer')
        mobile=browser.new_context(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True)
        mp=mobile.new_page()
        mp.goto(base+'/',wait_until='networkidle')
        expect(mp.locator('.menu-toggle')).to_be_visible()
        mp.locator('.menu-toggle').click()
        expect(mp.locator('.mobile-nav')).to_be_visible()
        assert mp.locator('.mobile-nav a[href="'+reserve+'"]').count()==1, 'Mobile reserve link missing'
        assert mp.locator('.mobile-bottom-cta__primary[href="'+reserve+'"]').count()==1, 'Mobile booking CTA missing'
        # The mobile menu must navigate to delivery and Loona without remaining open.
        mp.locator('.mobile-nav a[href="/#delivery"]').click()
        expect(mp.locator('.mobile-nav')).not_to_be_visible()
        expect(mp.locator('#delivery')).to_be_visible()
        assert mp.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'), 'Horizontal scroll on mobile home'
        mp.locator('.menu-toggle').click()
        mp.locator('.mobile-nav a[href="/menu/"]').click()
        expect(mp.locator('.print-card')).to_have_count(5)
        expect(mp.locator('.menu-items .dish img')).to_have_count(0)
        mp.locator('.print-card').first.click()
        expect(mp.locator('#menu-lightbox')).to_be_visible()
        expect(mp.locator('#menu-lightbox-prev')).to_be_hidden()
        expect(mp.locator('#menu-lightbox-next')).to_be_hidden()
        img_width=mp.locator('#menu-lightbox-image').bounding_box()['width']
        assert img_width >= 350, f'Mobile single-page menu image too narrow: {img_width}'
        mp.locator('#menu-lightbox-close').click()
        assert mp.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'), 'Horizontal scroll on mobile menu'
        mp.screenshot(path=str(REPORT/'menu-mobile.png'),full_page=True)
        mp.goto(base+'/',wait_until='networkidle')
        for img in mp.locator('.gallery-grid img:visible, .events-photo img:visible').all():
            img.scroll_into_view_if_needed()
            img.evaluate('(e) => e.decode()')
            assert loaded(img), 'Mobile restaurant photograph failed to load'
        mp.locator('h1').scroll_into_view_if_needed()
        mp.screenshot(path=str(REPORT/'home-mobile.png'),full_page=True)
        print('PASS: mobile delivery navigation, no horizontal scroll or old food images; five menu cards')
        # At minimum supported phone width, content must not force sideways scrolling.
        narrow=browser.new_context(viewport={'width':320,'height':720},is_mobile=True,has_touch=True)
        np=narrow.new_page()
        for route in ('/','/menu/','/banquets/','/contacts/','/privacy/'):
            np.goto(base+route,wait_until='domcontentloaded')
            np.wait_for_timeout(100)
            dimensions=np.evaluate('({viewport:innerWidth,scroll:document.documentElement.scrollWidth})')
            assert dimensions['scroll'] <= dimensions['viewport']+2, f'Horizontal overflow at 320px on {route}: {dimensions}'
        narrow.close()
        print('PASS: no horizontal scrolling at 320px across all five pages')
        # Consent regression: no Yandex request before opt-in, including after opt-out.
        consent=desktop.new_page()
        metrika_requests=[]
        consent.route('https://mc.yandex.ru/metrika/tag.js?id=113768615',lambda route: route.fulfill(status=200,content_type='application/javascript',body=''))
        consent.on('request',lambda req: metrika_requests.append(req.url) if req.url.startswith('https://mc.yandex.ru/') else None)
        consent.goto(base+'/',wait_until='networkidle')
        expect(consent.locator('.cookie-banner')).to_be_visible()
        assert not metrika_requests,'Metrika must not request external scripts before consent'
        consent.locator('[data-consent="no"]').click()
        consent.reload(wait_until='networkidle')
        assert not metrika_requests,'Denied analytics must remain disabled after reload'
        expect(consent.locator('.cookie-banner')).to_have_count(0)
        consent.locator('.cookie-settings').click()
        expect(consent.locator('.cookie-banner')).to_be_visible()
        consent.locator('[data-consent="yes"]').click()
        consent.wait_for_function("window.ym?.a?.some(x=>x[1]==='init' && x[0]===113768615)",timeout=10000)
        assert len(metrika_requests)==1, f'Exactly one tagged script expected after consent: {metrika_requests}'
        consent.evaluate("""() => {
          const a=document.querySelector('[data-track="menu_from_hero"]');
          a.addEventListener('click',event=>event.preventDefault(),{once:true});
          a.click();
        }""")
        consent.wait_for_function("window.ym?.a?.some(x=>x[1]==='reachGoal' && x[2]==='menu_from_hero' && x[0]===113768615)",timeout=10000)
        print('PASS: Yandex Metrika 113768615 loads only after opt-in, rejected opt-in stays rejected, reachGoal fires')
        assert not page_errors,'Unexpected page JavaScript errors: '+str(page_errors)
        consent.close()
        desktop.close()
        mobile.close()
        browser.close()
finally:
    server.terminate()
    try:server.wait(timeout=5)
    except subprocess.TimeoutExpired:server.kill()
print('BROWSER QA SUCCESS:',REPORT)
