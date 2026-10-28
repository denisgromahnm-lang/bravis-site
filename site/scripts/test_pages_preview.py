#!/usr/bin/env python3
"""Verify prepared GitHub Pages project subpath, without contacting external networks."""
import json
import re
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'dist'
prefix='/bravis-site/'
assert (root/'404.html').is_file()
for page in ('index.html','menu/index.html','lunch/index.html','banquets/index.html','contacts/index.html','privacy/index.html'):
    doc=(root/page).read_text(encoding='utf-8')
    for field,value in re.findall(r'(href|src)=["\']([^"\']+)["\']',doc):
        if value.startswith('/') and not value.startswith(prefix):
            raise AssertionError(f'Preview path is unprefixed: {page} {field}={value}')
    assert 'name="robots" content="noindex' in doc
    assert 'href="'+prefix+'assets/site.css"' in doc
    assert 'src="'+prefix+'assets/site.js"' in doc
menu=(root/'menu/index.html').read_text(encoding='utf8')
match=re.search(r'<script type="application/json" id="bravis-menu-data">(.*?)</script>',menu,re.S)
assert match,'Menu viewer manifest absent'
data=json.loads(match.group(1))
assert len(data)==5
for m in data:
    for image in m['pages']:
        assert image.startswith(prefix+'menu-media/'),f'Menu lightbox image not prefixed: {image}'
        assert (root/image[len(prefix):]).is_file(),image
assert 'href="'+prefix+'privacy/"' in menu
js=(root/'assets/site.js').read_text(encoding='utf8')
assert "privacyHref" in js,'Cookie banner must derive route rather than hardcode it'
print('PASS: GitHub Pages links, image viewer, privacy consent route and noindex')
