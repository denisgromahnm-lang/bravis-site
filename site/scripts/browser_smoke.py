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
        page.goto(base+'/',wait_until='networkidle',timeout=30000)
        expect(page.locator('h1')).to_contain_text('Вкус встреч')
        expect(page.locator('.hero-photo')).to_be_visible()
        assert loaded(page.locator('.hero-photo')),'Hero image failed to load'
        assert page.locator('html').get_attribute('lang')=='ru'
        assert 'noindex' in page.locator('meta[name="robots"]').get_attribute('content')
        page.screenshot(path=str(REPORT/'home-desktop.png'),full_page=True)
        print('PASS: desktop hero, image, metadata, home screenshot')
        page.goto(base+'/menu/',wait_until='networkidle')
        expect(page.locator('.print-card')).to_have_count(5)
        for i in range(5):
            thumb=page.locator('.print-card__image img').nth(i)
            thumb.scroll_into_view_if_needed()
            assert loaded(thumb),f'Menu cover {i+1} broken'
        page.locator('.print-card').first.click()
        dialog=page.locator('#menu-lightbox')
        expect(dialog).to_be_visible()
        expect(page.locator('#menu-lightbox-image')).to_be_visible()
        assert loaded(page.locator('#menu-lightbox-image')),'Menu full-screen image missing'
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
        mp.locator('.mobile-nav a[href="/menu/"]').click()
        expect(mp.locator('.print-card')).to_have_count(5)
        mp.screenshot(path=str(REPORT/'menu-mobile.png'),full_page=True)
        print('PASS: touch-size navigation and five readable menu cards on mobile')
        desktop.close()
        mobile.close()
        browser.close()
finally:
    server.terminate()
    try:server.wait(timeout=5)
    except subprocess.TimeoutExpired:server.kill()
print('BROWSER QA SUCCESS:',REPORT)
