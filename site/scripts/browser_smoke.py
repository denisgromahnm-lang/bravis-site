#!/usr/bin/env python3
"""BRAVIS automated browser acceptance: desktop/mobile, menu reader and nav.
Outputs three screenshots in site/browser-report without touching production servers.
"""
import contextlib
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
import re
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

def accept_gallery_and_messengers(browser):
    """Inspect actual responsive photographs and contact choices without sending."""
    config=json.loads((ROOT/'site.config.json').read_text(encoding='utf8'))
    max_url=config['socialLinks']['max']
    for width,columns in ((320,1),(768,2),(1440,3)):
        context=browser.new_context(viewport={'width':width,'height':900},java_script_enabled=False)
        context.route('**/*',lambda route: route.continue_() if route.request.url.startswith(base+'/') else route.abort())
        page=context.new_page()
        page.goto(base+'/gallery/',wait_until='networkidle')
        page.screenshot(path=str(REPORT/f'gallery-{width}.png'),full_page=False)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'), 'Gallery overflow at '+str(width)
        expect(page.locator('.restaurant-gallery img')).to_have_count(10)
        assert page.locator('.restaurant-gallery__columns').evaluate('(e)=>getComputedStyle(e).columnCount')==str(columns)
        assert len(set(page.locator('.restaurant-gallery img').evaluate_all('(items)=>items.map(e=>e.getAttribute("src"))')))==10
        for img in page.locator('.restaurant-gallery img').all():
            expect(img).to_have_attribute('loading','lazy')
            expect(img).to_have_attribute('decoding','async')
            img.scroll_into_view_if_needed()
            expect(img).to_have_js_property('complete',True)
            assert loaded(img), 'Gallery original did not load'
            assert img.evaluate('(e)=>Number(e.getAttribute("width"))===e.naturalWidth && Number(e.getAttribute("height"))===e.naturalHeight'), 'Gallery dimensions do not match the original'
            assert img.evaluate('(e)=>Math.abs(e.getBoundingClientRect().width/e.getBoundingClientRect().height-e.naturalWidth/e.naturalHeight)<.01'), 'Gallery photograph was cropped'
        page.goto(base+'/banquets/',wait_until='networkidle')
        page.screenshot(path=str(REPORT/f'banquet-messengers-{width}.png'),full_page=False)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'), 'Banquet overflow at '+str(width)
        choices=page.locator('.banquet-messengers__links')
        assert choices.count()>=3, 'Messenger choices missing in a banquet conversion block'
        for group in choices.all():
            expect(group.locator('a')).to_have_count(3)
            assert group.locator('a>span').all_text_contents()==['WhatsApp','Telegram','MAX']
            assert group.locator('a').nth(0).get_attribute('href').startswith('https://wa.me/79895719977?text=')
            expect(group.locator('a').nth(1)).to_have_attribute('href','https://t.me/+79895719977')
            expect(group.locator('a').nth(2)).to_have_attribute('href',max_url)
            for link in group.locator('a').all():
                assert link.get_attribute('aria-label')
                expect(link).to_have_attribute('rel','noopener noreferrer')
                expect(link).to_have_attribute('target','_blank')
                rect=link.bounding_box()
                assert rect['width']>=44 and rect['height']>=44, 'Messenger target too small'
        for route in ('/menu/','/lunch/'):
            page.goto(base+route,wait_until='networkidle')
            expect(page.locator('.bravis-lunch-reward')).to_contain_text('Шестой бизнес-ланч — бесплатно')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'), 'Lunch reward overflow at '+str(width)
        page.goto(base+'/',wait_until='networkidle')
        expect(page.locator('.bravis-offer--lunch .bravis-lunch-tag')).to_contain_text('Бесплатно')
        expect(page.locator('.bravis-offer--lunch')).to_contain_text('каждый шестой бизнес-ланч')
        context.close()
    header_context=browser.new_context(viewport={'width':1440,'height':900})
    header=header_context.new_page()
    for width in (1024,1440):
        header.set_viewport_size({'width':width,'height':900})
        header.goto(base+'/gallery/',wait_until='networkidle')
        assert header.evaluate('document.documentElement.scrollWidth<=innerWidth+2'), 'Header overflow at '+str(width)
        if width==1024:
            expect(header.locator('.desktop-nav')).not_to_be_visible()
            expect(header.locator('.menu-toggle')).to_be_visible()
            header.locator('.menu-toggle').click()
            expect(header.locator('.mobile-nav a[href="/gallery/"]')).to_be_visible()
        else:
            expect(header.locator('.desktop-nav a[href="/gallery/"]')).to_be_visible()
            boxes=[header.locator(selector).bounding_box() for selector in ('.logo','.desktop-nav','.header-actions')]
            assert all(boxes), 'Header element missing'
            assert boxes[0]['x']+boxes[0]['width']<=boxes[1]['x'] and boxes[1]['x']+boxes[1]['width']<=boxes[2]['x'], 'Desktop navigation overlaps logo or booking'
    header_context.close()
    print('PASS: 10 uncropped responsive gallery originals, sixth lunch offer and direct WhatsApp/Telegram/MAX choices; headers at 1024/1440')

def accept_event_clock(browser):
    """A reading leaves Today at Moscow midnight; Friday/Saturday music repeats."""
    reading='chekhov-readings-2026-10-30'
    for instant,music,readings in (
            (datetime(2026,10,30,15,tzinfo=timezone.utc),1,1),
            (datetime(2026,10,31,17,tzinfo=timezone.utc),1,0),
            (datetime(2026,11,1,17,tzinfo=timezone.utc),0,0)):
        context=browser.new_context(viewport={'width':390,'height':844},timezone_id='America/Los_Angeles')
        context.route('**/*',lambda route: route.continue_() if route.request.url.startswith(base+'/') else route.abort())
        page=context.new_page()
        page.clock.install(time=instant)
        page.goto(base+'/events/',wait_until='networkidle')
        today=page.locator('[data-restaurant-life-part="today"]')
        expect(today.locator('[data-life-id="live-music"]')).to_have_count(music)
        expect(today.locator('[data-life-id="'+reading+'"]')).to_have_count(readings)
        expect(page.locator('[data-restaurant-life-part="news"] [data-life-id="'+reading+'"]')).to_contain_text('19:00')
        ids=today.locator('[data-life-id]').evaluate_all('(items)=>items.map(e=>e.dataset.lifeId)')
        assert len(ids)==len(set(ids)), 'Duplicate Today cards'
        context.close()
    boundary=browser.new_context(timezone_id='America/Los_Angeles')
    boundary.route('**/*',lambda route: route.continue_() if route.request.url.startswith(base+'/') else route.abort())
    page=boundary.new_page()
    page.clock.install(time=datetime(2026,10,30,20,59,30,tzinfo=timezone.utc))
    navigations=[]
    page.on('framenavigated',lambda frame:navigations.append(frame.url) if frame==page.main_frame else None)
    page.goto(base+'/events/',wait_until='networkidle')
    today=page.locator('[data-restaurant-life-part="today"]')
    expect(today.locator('[data-life-id="'+reading+'"]')).to_have_count(1)
    page.clock.fast_forward(61000)
    page.clock.run_for(100)
    expect(today.locator('[data-life-id="'+reading+'"]')).to_have_count(0)
    expect(today.locator('[data-life-id="live-music"]')).to_have_count(1)
    expect(page.locator('[data-restaurant-life-part="news"] [data-life-id="'+reading+'"]')).to_have_count(1)
    assert len(navigations)==1, 'Moscow midnight reloaded the page'
    boundary.close()
    print('PASS: 30 October reading at 19:00, Friday/Saturday music, Sunday fallback and Moscow midnight update without navigation')

def accept_public_revision(browser):
    """Exercise the public menu/editorial change, including an already open page."""
    def guest_brand(page):
        text=page.locator('body').inner_text()
        labels=page.locator('[alt],[aria-label],[title]').evaluate_all(
            '(nodes)=>nodes.flatMap(node=>["alt","aria-label","title"].map(key=>node.getAttribute(key)||"")).join(" ")')
        assert not re.search(r'loona|luna|луна',text+' '+labels,re.I), 'Provider name leaked into guest marketing'

    nojs=browser.new_context(viewport={'width':320,'height':720},java_script_enabled=False)
    nojs.route('**/*',lambda route: route.continue_() if route.request.url.startswith(base+'/') else route.abort())
    static=nojs.new_page()
    for route in ('/','/go/','/events/','/menu/'):
        static.goto(base+route,wait_until='networkidle')
        guest_brand(static)
        assert static.evaluate('document.documentElement.scrollWidth<=innerWidth+2'), 'Static page overflow: '+route
        if route=='/':
            expect(static.locator('.loyalty-action')).to_have_attribute('href','https://app.loona.ai/4992/create/register?source=qr&tag=none')
            assert static.locator('a[href="/events/"]').count()>0
        elif route=='/events/':
            for part in ('today','formats','news'):
                expect(static.locator('[data-restaurant-life-part="'+part+'"]').get_by_role('heading',level=2)).to_be_visible()
            assert static.locator('[data-restaurant-life-part="news"] time[datetime]').count()>0
        elif route=='/menu/':
            assert static.locator('.print-card').evaluate_all('(items)=>items.map(item=>item.getAttribute("href"))')==[
                '/menu-media/'+name+'.jpg' for name in ('main-front','main-back','business','children')]
            assert '/menu-media/seasonal.jpg' not in static.content()
    nojs.close()

    data=json.loads((DIST/'assets/restaurant-life.json').read_text(encoding='utf8'))
    current={'payload':deepcopy(data)}
    requests=[]
    context=browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce',timezone_id='America/Los_Angeles')
    def intercept(route):
        request=route.request
        requests.append((request.method,request.url))
        if request.url.split('?',1)[0]==base+'/assets/restaurant-life.json':
            route.fulfill(status=200,content_type='application/json; charset=utf-8',body=json.dumps(current['payload'],ensure_ascii=False))
        elif request.url.startswith(base+'/'):
            route.continue_()
        else:
            route.abort()
    context.route('**/*',intercept)
    live=context.new_page()
    live.clock.install(time=datetime(2026,11,2,12,59,30,tzinfo=timezone.utc))
    navigations=[];errors=[]
    live.on('framenavigated',lambda frame: navigations.append(frame.url) if frame==live.main_frame else None)
    live.on('pageerror',lambda error: errors.append(str(error)))
    live.goto(base+'/events/',wait_until='networkidle')
    guest_brand(live)
    today=live.locator('[data-restaurant-life-part="today"]')
    news=live.locator('[data-restaurant-life-part="news"]')
    expect(today.locator('[data-life-id="lunch"]')).to_have_count(1)
    assert any(url.split('?',1)[0]==base+'/assets/restaurant-life.json' for _,url in requests), 'Initial live-content fetch missing'
    if live.locator('[data-consent="no"]').count():live.locator('[data-consent="no"]').click()
    anchor=live.locator('#bravis-formats-heading')
    anchor.scroll_into_view_if_needed()
    live.evaluate('(y)=>scrollTo({top:y,behavior:"instant"})',anchor.bounding_box()['y']+live.evaluate('scrollY')-120)
    live.locator('.logo').evaluate('(node)=>node.focus({preventScroll:true})')
    anchor_y=anchor.bounding_box()['y']

    def revised(title):
        candidate=deepcopy(data)
        candidate['news'][0]['title']=title
        candidate.pop('revision',None)
        encoded=json.dumps(candidate,ensure_ascii=False,sort_keys=True,separators=(',',':'))
        candidate['revision']=sha256(encoded.encode()).hexdigest()[:20]
        return candidate

    def refresh():
        with live.expect_response(lambda response: response.url.split('?',1)[0]==base+'/assets/restaurant-life.json') as response:
            live.clock.fast_forward(61000)
        response.value.body()
        live.clock.run_for(50)

    # A Moscow lunch boundary must refresh even when server content is unchanged.
    refresh()
    expect(today.locator('[data-life-id="lunch"]')).to_have_count(0)
    assert abs(anchor.bounding_box()['y']-anchor_y)<=2, 'Moscow clock refresh moved the visible reading position'

    current['payload']=revised('Новость проверки без перезагрузки')
    refresh()
    expect(news.locator('h3').first).to_have_text('Новость проверки без перезагрузки')
    assert abs(anchor.bounding_box()['y']-anchor_y)<=2, 'Live update moved the visible reading position'

    # Keep a focused link stable while its region receives a newer revision.
    focused=news.locator('a').first
    focused.focus()
    handle=focused.element_handle()
    current['payload']=revised('Новость после завершения взаимодействия')
    refresh()
    expect(news.locator('h3').first).to_have_text('Новость проверки без перезагрузки')
    assert handle.evaluate('(node)=>node.isConnected && node===document.activeElement'), 'Update replaced the focused news link'
    live.locator('.logo').evaluate('(node)=>node.focus({preventScroll:true})')
    live.clock.run_for(50)
    expect(news.locator('h3').first).to_have_text('Новость после завершения взаимодействия')

    current['payload']={'schemaVersion':999,'revision':'invalid'}
    refresh()
    expect(news.locator('h3').first).to_have_text('Новость после завершения взаимодействия')
    assert len(navigations)==1, 'Live content refreshed by navigating/reloading the document'
    assert all(method=='GET' for method,_ in requests), 'Editorial refresh made a mutating request'
    assert not any('app.loona.ai' in url or '5047' in url for _,url in requests), 'Editorial refresh requested a checkout/account service'
    assert not errors, errors
    context.close()
    print('PASS: four public menus, BRAVIS-only marketing, static events, in-place revision/Moscow clock, scroll/focus preservation and malformed-feed fallback')
try:
    with sync_playwright() as p:
        browser_path=os.environ.get('BRAVIS_CHROMIUM_EXECUTABLE') or shutil.which('chromium')
        browser=p.chromium.launch(executable_path=browser_path,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        accept_gallery_and_messengers(browser)
        accept_event_clock(browser)
        accept_public_revision(browser)
        if '--public-revision-only' in sys.argv:
            browser.close()
            raise SystemExit(0)
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
        assert loaded(page.locator('.loyalty-qr img')),'Guest card enrollment QR did not load'
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
        expect(page.locator('.print-card')).to_have_count(4)
        # The owner rejected old dish thumbnails: printed menu covers are retained,
        # but each textual dish is intentionally shown without a food photograph.
        expect(page.locator('.menu-items .dish img')).to_have_count(0)
        assert page.locator('.menu-items .dish').count()>=60, 'Textual menu items missing'
        for i in range(4):
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
        expect(page.locator('#menu-original')).to_have_attribute('href','/menu-media/main-front.jpg')
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
        print('PASS: four published menu thumbnails and full-screen viewer')
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
        # The mobile menu must navigate to delivery and the guest card without remaining open.
        mp.locator('.mobile-nav a[href="/#delivery"]').click()
        expect(mp.locator('.mobile-nav')).not_to_be_visible()
        expect(mp.locator('#delivery')).to_be_visible()
        assert mp.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'), 'Horizontal scroll on mobile home'
        mp.locator('.menu-toggle').click()
        mp.locator('.mobile-nav a[href="/menu/"]').click()
        expect(mp.locator('.print-card')).to_have_count(4)
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
        print('PASS: mobile delivery navigation, no horizontal scroll or old food images; four published menu cards')
        # At minimum supported phone width, content must not force sideways scrolling.
        narrow=browser.new_context(viewport={'width':320,'height':720},is_mobile=True,has_touch=True)
        np=narrow.new_page()
        for route in ('/','/menu/','/lunch/','/banquets/','/contacts/','/privacy/','/go/','/events/','/gallery/'):
            np.goto(base+route,wait_until='domcontentloaded')
            np.wait_for_timeout(100)
            dimensions=np.evaluate('({viewport:innerWidth,scroll:document.documentElement.scrollWidth})')
            assert dimensions['scroll'] <= dimensions['viewport']+2, f'Horizontal overflow at 320px on {route}: {dimensions}'
        narrow.close()
        print('PASS: no horizontal scrolling at 320px across all nine pages')
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
            expect(navpage.locator('.print-card')).to_have_count(4)
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
        # Verify desktop return after an explicit long scroll; resizing may settle
        # the prior mobile anchor animation at a different scroll position.
        navpage.evaluate('window.scrollTo({top:1200,behavior:"instant"})')
        navpage.wait_for_function('scrollY > 400')
        expect(navpage.locator('.back-to-top')).to_be_visible()
        navpage.locator('.back-to-top').click()
        navpage.wait_for_function('scrollY <= 1',timeout=5000)
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
        expect(wp.get_by_role('button',name='Проверить актуальный рейтинг')).to_have_count(0)
        expect(wp.locator('[data-yandex-widget="rating"]')).to_have_count(0)
        wp.get_by_role('button',name='Показать карту здесь',exact=True).click()
        expect(wp.locator('[data-yandex-widget="map"] iframe')).to_have_attribute('src','https://yandex.ru/map-widget/v1/?ol=biz&oid=120928769508&z=16')
        wp.get_by_role('button',name='Закрыть карту',exact=True).click()
        expect(wp.locator('[data-yandex-widget="map"] iframe')).to_have_count(0)
        expect(wp.get_by_role('button',name='Показать карту здесь',exact=True)).to_be_visible()
        assert not any('rating-badge' in url for url in requested), 'Removed rating widget still requested'
        wp.goto(base+'/404.html',wait_until='domcontentloaded')
        expect(wp.locator('h1')).to_contain_text('не найдена')
        expect(wp.locator('meta[name="robots"]')).to_have_attribute('content','noindex, nofollow')
        expect(wp.locator('link[rel="canonical"]')).to_have_count(0)
        widgets.close()
        print('PASS: verified communities, no rating loader, closeable opt-in map and branded noindex 404')
        consent_context.close()
        desktop.close()
        mobile.close()
        browser.close()
finally:
    server.terminate()
    try:server.wait(timeout=5)
    except subprocess.TimeoutExpired:server.kill()
print('BROWSER QA SUCCESS:',REPORT)
