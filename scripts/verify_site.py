#!/usr/bin/env python3
"""BRAVIS static output checks; no dependencies, network or secrets."""
import json, re
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DIST=ROOT/'dist'
paths=['index.html','menu/index.html','banquets/index.html','contacts/index.html','privacy/index.html']
class Links(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.images=[];self.scripts=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='a' and a.get('href'):self.links.append(a['href'])
        if tag=='img' and a.get('src'):self.images.append(a['src'])
        if tag=='script' and a.get('src'):self.scripts.append(a['src'])
assert all((DIST/p).is_file() for p in paths),'Missing HTML page'
for path in paths:
    html=(DIST/path).read_text(encoding='utf-8')
    assert '<html lang="ru">' in html and '<title>' in html,path
    assert 'name="description"' in html and 'name="viewport"' in html,path
    assert '<main' in html and '<h1' in html,path
    assert 'application/ld+json' in html,path
    assert '<script' in html and 'site.js' in html,path
    doc=Links();doc.feed(html)
    for href in doc.images+doc.scripts+doc.links:
        if not href.startswith('/') or href.startswith('//'):continue
        rel=href.split('?',1)[0].split('#',1)[0].lstrip('/')
        target=DIST/rel
        if not rel or href.endswith('/'):target=target/'index.html'
        assert target.is_file(),f'Broken local URL {path} -> {href}'
if (ROOT/'site.config.json').exists():
    config=json.loads((ROOT/'site.config.json').read_text(encoding='utf-8'))
    if not config.get('public'):
        for p in paths:
            assert 'name="robots" content="noindex' in (DIST/p).read_text(encoding='utf-8'),p
        assert 'Disallow: /' in (DIST/'robots.txt').read_text(encoding='utf-8')
print('PASS: five BRAVIS pages, accessible links, local media assets, JSON-LD, preview noindex')
