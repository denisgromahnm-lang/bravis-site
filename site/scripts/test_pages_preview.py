#!/usr/bin/env python3
"""Verify prepared GitHub Pages project subpath, without contacting external networks."""
import json
import re
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'dist'
prefix='/bravis-site/'
assert (root/'404.html').is_file()
for page in ('index.html','menu/index.html','lunch/index.html','banquets/index.html','contacts/index.html','privacy/index.html','go/index.html','events/index.html','404.html'):
    doc=(root/page).read_text(encoding='utf-8')
    for field,value in re.findall(r'(href|src)=["\']([^"\']+)["\']',doc):
        if value.startswith('/') and not value.startswith(prefix):
            raise AssertionError(f'Preview path is unprefixed: {page} {field}={value}')
    assert 'name="robots" content="noindex' in doc
    assert re.search(r'href="'+re.escape(prefix)+r'assets/site\.css(?:\?v=[a-f0-9]{12})?"',doc)
    assert re.search(r'src="'+re.escape(prefix)+r'assets/site\.js(?:\?v=[a-f0-9]{12})?"',doc)
menu=(root/'menu/index.html').read_text(encoding='utf8')
match=re.search(r'<script type="application/json" id="bravis-menu-data">(.*?)</script>',menu,re.S)
assert match,'Menu viewer manifest absent'
data=json.loads(match.group(1))
assert len(data)==4, 'Only the four published menus belong in the viewer'
assert [item['pages'] for item in data]==[[prefix+'menu-media/'+name+'.jpg'] for name in ('main-front','main-back','business','children')]
assert prefix+'menu-media/seasonal.jpg' not in menu, 'Unpublished seasonal menu leaked into Pages'
for m in data:
    for image in m['pages']:
        assert image.startswith(prefix+'menu-media/'),f'Menu lightbox image not prefixed: {image}'
        assert (root/image[len(prefix):]).is_file(),image
assert 'href="'+prefix+'privacy/"' in menu
assert 'href="'+prefix+'events/"' in (root/'index.html').read_text(encoding='utf8'), 'Events link missing its project prefix'
js=(root/'assets/site.js').read_text(encoding='utf8')
assert "privacyHref" in js,'Cookie banner must derive route rather than hardcode it'
for stylesheet in root.rglob('*.css'):
    for value in re.findall(r"url\(\s*[\"']?(/[^)\"']+)",stylesheet.read_text(encoding='utf8')):
        assert value.startswith(prefix),f'Preview CSS artwork is unprefixed: {stylesheet.name} {value}'
        assert (root/value[len(prefix):]).is_file(),f'Missing CSS artwork: {value}'
print('PASS: GitHub Pages links, image viewer, privacy consent route and noindex')
