#!/usr/bin/env python3
"""BRAVIS static output checks; no dependencies, network or secrets."""
import json, re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DIST=ROOT/'dist'
paths=['index.html','menu/index.html','lunch/index.html','banquets/index.html','contacts/index.html','privacy/index.html','go/index.html','events/index.html','gallery/index.html']
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
        if not rel or rel.endswith('/'):target=target/'index.html'
        assert target.is_file(),f'Broken local URL {path} -> {href}'
missing=(DIST/'404.html').read_text(encoding='utf-8')
assert 'name="robots" content="noindex' in missing, '404 must not be indexed'
assert 'rel="canonical"' not in missing, '404 must not canonicalize to the home page'
assert 'Страница <em>не найдена.' in missing
if (DIST/'sitemap.xml').is_file():
    sitemap=ET.parse(DIST/'sitemap.xml')
    urls=[node.text for node in sitemap.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    expected=['https://bravisrest.ru'+('/' if p=='index.html' else '/'+p.removesuffix('index.html')) for p in paths]
    assert len(urls)==len(set(urls))==9, 'Sitemap must contain nine unique public pages'
    assert set(urls)==set(expected), 'Sitemap must retain every canonical public route and exclude 404'
if (ROOT/'site.config.json').exists():
    config=json.loads((ROOT/'site.config.json').read_text(encoding='utf-8'))
    if not config.get('public'):
        for p in paths:
            assert 'name="robots" content="noindex' in (DIST/p).read_text(encoding='utf-8'),p
        assert 'Disallow: /' in (DIST/'robots.txt').read_text(encoding='utf-8')
mode='public indexing' if config.get('public') else 'preview noindex'
print('PASS: nine BRAVIS pages, accessible links, local media assets, JSON-LD, '+mode)
