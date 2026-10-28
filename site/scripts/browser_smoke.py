#!/usr/bin/env python3
"""BRAVIS automated browser acceptance: desktop/mobile, menu reader and nav.
Outputs three screenshots in site/browser-report without touching production servers.
"""
import contextlib
import os
import shutil
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
        browser_path=os.environ.get('BRAVIS_CHROMIUM_EXECUTABLE') or shutil.which('chromium')
        browser=p.chromium.launch(executable_path=browser_path,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
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
        page.locator('.loyalty-qr img').scroll_into_view_if_needed()
        page.locator('.loyalty-qr img').evaluate('(image) => image.decode()')
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
        expect(page.locator('#menu-zoom-level')).to_have_text('100%')
        expect(page.locator('#menu-original')).to_have_attribute('href','/menu-media/seasonal.jpg')
        page.locator('#menu-zoom-in').click()
        expect(page.locator('#menu-zoom-level')).to_have_text('150%')
        stage=page.locator('#menu-lightbox-stage')
        stage.press('+')
        expect(page.locator('#menu-zoom-level')).to_have_text('200%')
        assert stage.evaluate('(e) => e.scrollWidth > e.clientWidth || e.scrollHeight > e.clientHeight'), 'Zoom did not enlarge the menu'
        stage.evaluate('(e) => {e.scrollTop=0;e.scrollLeft=0}')
        stage.press('ArrowDown')
        assert stage.evaluate('(e) => e.scrollTop > 0'), 'Keyboard panning failed'
        stage.press('0')
        expect(page.locator('#menu-zoom-level')).to_have_text('100%')
        stage.press('Escape')
        expect(dialog).not_to_be_visible()
        expect(page.locator('.print-card').first).to_be_focused()
        page.screenshot(path=str(REPORT/'menu-desktop.png'),full_page=True)
        print('PASS: five actual menu thumbnails and full-screen viewer')
        page.goto(base+'/lunch/',wait_until='networkidle')
        expect(page.get_by_role('heading',level=1)).to_contain_text('Пауза на')
        expect(page.get_by_role('tab',name='Понедельник',exact=True)).to_have_attribute('aria-selected','true')
        page.get_by_role('tab',name='Среда',exact=True).click()
        expect(page.locator('#lunch-wednesday')).to_be_visible()
        expect(page.locator('#lunch-monday')).to_be_hidden()
        expect(page.locator('#lunch-wednesday')).to_contain_text('Харчо с телятиной и ткемали')
        page.get_by_role('tab',name='Среда',exact=True).press('End')
        expect(page.get_by_role('tab',name='Пятница',exact=True)).to_be_focused()
        expect(page.locator('#lunch-friday')).to_be_visible()
        page.locator('.lunch-original summary').click()
        original=page.locator('.lunch-original img')
        original.scroll_into_view_if_needed()
        original.evaluate('(image) => image.decode()')
        assert loaded(original), 'Original lunch menu image failed to load'
        expect(page.locator('.lunch-original__body > a')).to_have_attribute('href','/menu-media/business.jpg')
        page.locator('.lunch-original summary').click()
        if page.locator('[data-consent="no"]').count(): page.locator('[data-consent="no"]').click()
        page.get_by_role('tab',name='Понедельник',exact=True).click()
        page.locator('h1').scroll_into_view_if_needed()
        page.screenshot(path=str(REPORT/'lunch-desktop.png'),full_page=True)
        nojs=browser.new_context(java_script_enabled=False)
        nj=nojs.new_page()
        nj.goto(base+'/lunch/',wait_until='domcontentloaded')
        expect(nj.locator('.lunch-day:visible')).to_have_count(5)
        expect(nj.locator('[data-lunch-tabs]')).to_be_hidden()
        nojs.close()
        print('PASS: lunch day selection, keyboard navigation, original menu and no-JavaScript fallback')
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
        mp.locator('#menu-zoom-in').click()
        mp.locator('#menu-zoom-in').click()
        expect(mp.locator('#menu-zoom-level')).to_have_text('200%')
        assert mp.locator('#menu-lightbox-stage').evaluate('(e) => e.scrollWidth > e.clientWidth'), 'Mobile menu cannot scroll sideways after zoom'
        mp.locator('#menu-zoom-fit').click()
        expect(mp.locator('#menu-zoom-level')).to_have_text('100%')
        mp.locator('#menu-lightbox-close').click()
        assert mp.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'), 'Horizontal scroll on mobile menu'
        mp.screenshot(path=str(REPORT/'menu-mobile.png'),full_page=True)
        mp.goto(base+'/lunch/',wait_until='networkidle')
        mp.get_by_role('tab',name='Среда',exact=True).click()
        expect(mp.locator('#lunch-wednesday')).to_be_visible()
        assert mp.evaluate('document.documentElement.scrollWidth <= innerWidth + 2'), 'Horizontal scroll on mobile lunch'
        if mp.locator('[data-consent="no"]').count(): mp.locator('[data-consent="no"]').click()
        mp.locator('h1').scroll_into_view_if_needed()
        mp.screenshot(path=str(REPORT/'lunch-mobile.png'),full_page=True)
        mp.goto(base+'/',wait_until='networkidle')
        for img in mp.locator('.gallery-grid img:visible, .events-photo img:visible').all():
            img.scroll_into_view_if_needed()
            img.evaluate('(e) => e.decode()')
            assert loaded(img), 'Mobile restaurant photograph failed to load'
        mp.locator('h1').scroll_into_view_if_needed()
        mp.screenshot(path=str(REPORT/'home-mobile.png'),full_page=True)
        mp.locator('.footer').screenshot(path=str(REPORT/'social-footer-mobile.png'))
        mp.evaluate('window.scrollTo({top:1200,behavior:"instant"})')
        expect(mp.locator('.back-to-top')).to_be_visible()
        mp.locator('.back-to-top').click()
        mp.wait_for_function('scrollY <= 1',timeout=5000)
        print('PASS: mobile delivery navigation, no horizontal scroll or old food images; five menu cards')
        # At minimum supported phone width, content must not force sideways scrolling.
        narrow=browser.new_context(viewport={'width':320,'height':720},is_mobile=True,has_touch=True)
        np=narrow.new_page()
        for route in ('/','/menu/','/lunch/','/banquets/','/contacts/','/privacy/'):
            np.goto(base+route,wait_until='domcontentloaded')
            np.wait_for_timeout(100)
            dimensions=np.evaluate('({viewport:innerWidth,scroll:document.documentElement.scrollWidth})')
            assert dimensions['scroll'] <= dimensions['viewport']+2, f'Horizontal overflow at 320px on {route}: {dimensions}'
        narrow.close()
        print('PASS: no horizontal scrolling at 320px across all six pages')
        # Long mobile pages keep their header and catalog usable in either scroll direction.
        navigation=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,reduced_motion='reduce')
        navpage=navigation.new_page()
        naverrors=[]
        navpage.on('pageerror',lambda error: naverrors.append(str(error)))
        for width,height in [(320,720),(390,844),(844,390),(960,600)]:
            navpage.set_viewport_size({'width':width,'height':height})
            navpage.goto(base+'/',wait_until='networkidle')
            expect(navpage.locator('.back-to-top')).to_be_hidden()
            # At the top, the announcement still occupies space above the sticky header.
            navpage.locator('.menu-toggle').click()
            initial_booking=navpage.locator('.mobile-nav > .btn')
            initial_booking.scroll_into_view_if_needed()
            assert initial_booking.bounding_box()['y']+initial_booking.bounding_box()['height']<=height, f'Initial dropdown clipped at {width}x{height}'
            navpage.locator('.menu-toggle').press('Escape')
            assert navpage.evaluate('scrollY')<=1, 'Opening navigation moved the page'
            navpage.evaluate('window.scrollTo(0,1000)')
            navpage.wait_for_function('scrollY >= 900')
            expect(navpage.locator('.back-to-top')).to_be_visible()
            for amount in [1000,750]:
                navpage.evaluate('(y) => window.scrollTo(0,y)',amount)
                assert abs(navpage.locator('.site-header').bounding_box()['y'])<=1, f'Header left the viewport at {width}px'
                expect(navpage.locator('.header-menu-link')).to_be_visible()
            button=navpage.locator('.back-to-top').bounding_box()
            assert button['width']>=44 and button['height']>=44, 'Return-to-top hit area too small'
            for selector in ['.cookie-banner','.mobile-bottom-cta']:
                item=navpage.locator(selector)
                if item.is_visible():
                    rect=item.bounding_box()
                    overlaps=button['x'] < rect['x']+rect['width'] and button['x']+button['width'] > rect['x'] and button['y'] < rect['y']+rect['height'] and button['y']+button['height'] > rect['y']
                    assert not overlaps, f'Return-to-top overlaps {selector} at {width}px'
            navpage.locator('.back-to-top').click()
            navpage.wait_for_function('scrollY <= 1')
            expect(navpage.locator('.logo')).to_be_focused()
            expect(navpage.locator('.back-to-top')).to_be_hidden()
            navpage.evaluate('window.scrollTo(0,1000)')
            navpage.locator('.menu-toggle').click()
            expect(navpage.locator('.mobile-nav')).to_be_visible()
            expect(navpage.locator('.cookie-banner')).to_be_hidden()
            expect(navpage.locator('.back-to-top')).to_be_hidden()
            booking=navpage.locator('.mobile-nav > .btn')
            booking.scroll_into_view_if_needed()
            rect=booking.bounding_box()
            assert rect['y']>=navpage.locator('.site-header').bounding_box()['height'], 'Dropdown booking is behind header'
            assert rect['y']+rect['height']<=height, f'Dropdown booking clipped at {width}x{height}'
            navpage.locator('.menu-toggle').press('Escape')
            expect(navpage.locator('.mobile-nav')).to_be_hidden()
            expect(navpage.locator('.menu-toggle')).to_be_focused()
            expect(navpage.locator('.cookie-banner')).to_be_visible()
            navpage.locator('.header-menu-link').click()
            expect(navpage).to_have_url(base+'/menu/')
            expect(navpage.locator('.print-card')).to_have_count(5)
            assert navpage.evaluate('document.documentElement.scrollWidth <= innerWidth + 2'), 'Navigation added horizontal overflow'
        navpage.set_viewport_size({'width':390,'height':844})
        navpage.goto(base+'/',wait_until='networkidle')
        navpage.locator('[data-consent="no"]').click()
        navpage.locator('.menu-toggle').click()
        navpage.locator('.mobile-nav a[href="/#delivery"]').click()
        navpage.wait_for_function('scrollY > 400')
        assert navpage.locator('#delivery').bounding_box()['y']>=navpage.locator('.site-header').bounding_box()['height'], 'Anchor hidden under sticky header'
        navpage.screenshot(path=str(REPORT/'navigation-mobile.png'))
        navpage.locator('.menu-toggle').click()
        navpage.set_viewport_size({'width':1200,'height':900})
        expect(navpage.locator('.mobile-nav')).to_be_hidden()
        assert not navpage.locator('body').evaluate('(e) => e.classList.contains("nav-open")'), 'Navigation left page locked after resize'
        expect(navpage.locator('.back-to-top')).to_be_hidden()
        assert not naverrors, 'Mobile navigation runtime errors: '+str(naverrors)
        navigation.close()
        print('PASS: sticky mobile header, direct menu, back-to-top, unobscured anchors and scrollable landscape navigation')
        # Consent regression: no Yandex request before opt-in, including after opt-out.
        consent_context=browser.new_context()
        consent=consent_context.new_page()
        metrika_requests=[]
        consent.route('https://mc.yandex.com/metrika/tag.js?id=113768615',lambda route: route.fulfill(status=200,content_type='application/javascript',body=''))
        consent.on('request',lambda req: metrika_requests.append(req.url) if req.url.startswith('https://mc.yandex.com/') else None)
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
        blocked=browser.new_context()
        blocked.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw new DOMException('Storage blocked','SecurityError')}})")
        bp=blocked.new_page()
        bp.route('https://mc.yandex.com/**',lambda route: route.fulfill(status=200,content_type='application/javascript',body=''))
        bp.goto(base+'/',wait_until='networkidle')
        expect(bp.locator('.cookie-banner')).to_be_visible()
        assert not bp.evaluate('typeof window.ym === "function"'), 'Blocked storage must default to no analytics'
        bp.locator('[data-consent="yes"]').click()
        bp.wait_for_function("window.ym?.a?.some(x=>x[1]==='init')")
        blocked.close()
        # Public social links and external widgets must not load a third party before a visitor asks.
        widgets=browser.new_context()
        wp=widgets.new_page()
        requested=[]
        widgets.route('https://yandex.ru/**', lambda route: route.fulfill(status=200,content_type='text/html',body='<html lang="ru"><body>Widget test</body></html>'))
        wp.on('request', lambda req: requested.append(req.url) if req.url.startswith('https://yandex.ru/') else None)
        wp.goto(base+'/contacts/',wait_until='networkidle')
        expect(wp.locator('.social-links a[href="https://t.me/bravisrest"]')).to_have_count(2)
        expect(wp.locator('.social-links a[href="https://vk.com/bravisrest"]')).to_have_count(2)
        expect(wp.locator('.social-links a[href="https://wa.me/79895719977"]')).to_have_count(2)
        expect(wp.locator('.social-links a[href="https://t.me/+79895719977"]')).to_have_count(2)
        expect(wp.get_by_role('link',name='Instagram BRAVIS',exact=True)).to_have_count(2)
        for link in wp.locator('.social-links a').all():
            assert link.get_attribute('aria-label'), 'Icon-only social link needs an accessible name'
            expect(link.locator('svg')).to_have_count(1)
            expect(link.locator('svg')).to_have_attribute('aria-hidden','true')
            rect=link.bounding_box()
            assert rect['width']>=44 and rect['height']>=44, 'Social icon hit area too small'
        expect(wp.locator('.footer .yandex-award')).to_contain_text('5,0')
        expect(wp.locator('.footer .yandex-award')).to_contain_text('Хорошее место')
        expect(wp.locator('.footer .yandex-award')).to_contain_text('2026')
        expect(wp.locator('.footer .yandex-award')).to_have_attribute('href','https://yandex.ru/maps/org/bravis/120928769508/')
        assert not requested, 'Yandex widgets loaded without visitor action'
        wp.locator('[data-yandex-widget="rating"] button').click()
        expect(wp.locator('[data-yandex-widget="rating"] iframe')).to_have_attribute('src','https://yandex.ru/sprav/widget/rating-badge/120928769508?type=rating')
        wp.locator('[data-yandex-widget="map"] button').click()
        expect(wp.locator('[data-yandex-widget="map"] iframe')).to_have_attribute('src','https://yandex.ru/map-widget/v1/?ol=biz&oid=120928769508&z=16')
        wp.goto(base+'/404.html',wait_until='domcontentloaded')
        expect(wp.locator('h1')).to_contain_text('не найдена')
        expect(wp.locator('meta[name="robots"]')).to_have_attribute('content','noindex, nofollow')
        expect(wp.locator('link[rel="canonical"]')).to_have_count(0)
        widgets.close()
        print('PASS: verified communities, click-to-load Yandex rating/map and branded noindex 404')
        consent_context.close()
        desktop.close()
        mobile.close()
        browser.close()
finally:
    server.terminate()
    try:server.wait(timeout=5)
    except subprocess.TimeoutExpired:server.kill()
print('BROWSER QA SUCCESS:',REPORT)
