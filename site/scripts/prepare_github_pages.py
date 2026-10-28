#!/usr/bin/env python3
"""Make a noindex GitHub Pages preview under /bravis-site/ without changing real-domain code."""
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'dist'
PREFIX='/bravis-site'
for page in sorted(DIST.rglob('*.html')):
    data=page.read_text(encoding='utf8')
    data=re.sub(r'(href|src|content)=(["\'])/(?!/)',lambda m: m.group(1)+'='+m.group(2)+PREFIX+'/',data)
    # The lightbox image URLs are embedded in JSON strings, not HTML attributes.
    data=data.replace('"/menu-media/','"'+PREFIX+'/menu-media/')
    assert 'name="robots" content="noindex' in data
    page.write_text(data,encoding='utf8')
assert (DIST/'404.html').is_file(), 'Branded 404 must be generated before preparing the preview'
print('GitHub Pages preview built at /bravis-site/ (noindex)')
