#!/usr/bin/env python3
"""Synthetic table routes: exact destinations, safe fallback and mobile layout."""
from pathlib import Path
import sys
import json
import tempfile
import threading
import http.server
import functools
import shutil
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from table_hub import verified_tables, render_table_hub

config = json.loads((ROOT / 'site.config.json').read_text())
settings = {'approvedOrderHosts': ['orders.example.invalid'], 'tables': [
    {'id': '12', 'label': 'Пример: стол 12', 'orderUrl': 'https://orders.example.invalid/qr?table=original12&token=a%2Fb#menu'},
    {'id': '13', 'label': 'Пример: стол 13', 'orderUrl': 'https://orders.example.invalid/qr?table=original13&token=c%2Bd#menu'},
]}
tables = verified_tables(settings)
assert verified_tables({'tables': []}) == []
for bad in ['javascript:alert(1)', 'http://orders.example.invalid/qr', 'https://staff:password@orders.example.invalid/qr', 'https://another.example.invalid/qr', 'https://orders.example.invalid/qr\n']:
    try:
        verified_tables(dict(settings, tables=[dict(tables[0], orderUrl=bad)]))
    except ValueError:
        pass
    else:
        raise AssertionError('Unsafe order destination accepted')
for invalid in [dict(settings, tables=[tables[0], tables[0]]), dict(settings, tables=[dict(tables[0], id='../12')])]:
    try:
        verified_tables(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError('Ambiguous table routing accepted')

head = '<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><link rel="stylesheet" href="/assets/site.css"></head><body>'
class Links(HTMLParser):
    def __init__(self, document):
        super().__init__(); self.links = []; self.feed(document)
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and 'data-track' in attrs:
            self.links.append(attrs)

actual = verified_tables(json.loads((ROOT / 'content/table-links.json').read_text()))
for table in actual:
    document = (ROOT / 'dist/t' / table['id'] / 'index.html').read_text()
    links = Links(document).links
    assert [link['href'] for link in links] == [table['orderUrl'], config['loonaJoinUrl']]
    assert 'noindex, nofollow' in document

with tempfile.TemporaryDirectory(prefix='bravis-table-review-') as directory:
    folder = Path(directory)
    shutil.copytree(ROOT / 'public/assets', folder / 'assets')
    for table in [None] + tables:
        path = folder / 't' / (table['id'] if table else '')
        path.mkdir(parents=True, exist_ok=True)
        document = render_table_hub(config, head, table)
        (path / 'index.html').write_text(document)
        links = Links(document).links
        assert links[-1]['href'] == config['loonaJoinUrl']
        if table:
            assert len(links) == 2 and links[0]['href'] == table['orderUrl']
            other = tables[1] if table['id'] == '12' else tables[0]
            assert other['orderUrl'] not in document
        else:
            assert len(links) == 1 and 'aria-disabled="true"' in document
    from playwright.sync_api import sync_playwright, expect
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args): pass
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=directory))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    report = ROOT / 'browser-report' / 'table-hub'; report.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=shutil.which('chromium'), headless=True, args=['--no-sandbox'])
            for width in (320, 390, 1440):
                context = browser.new_context(viewport={'width': width, 'height': 900})
                context.route('**/*', lambda route: route.continue_() if route.request.url.startswith('http://127.0.0.1:') else route.abort())
                page = context.new_page()
                for route in ('/t/12/', '/t/13/', '/t/'):
                    page.goto(f'http://127.0.0.1:{server.server_port}' + route, wait_until='networkidle')
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                    expect(page.locator('.table-actions > *')).to_have_count(2)
                    for link in page.locator('.table-actions a').all():
                        assert link.bounding_box()['height'] >= 44
                    if route == '/t/12/':
                        page.screenshot(path=str(report / f'table-preview-{width}.png'))
                context.close()
            browser.close()
    finally:
        server.shutdown(); server.server_close()
print('PASS: distinct table destinations preserved exactly; unsafe mappings rejected; no-table fallback; two actions at320/390/1440; no external requests or orders')
