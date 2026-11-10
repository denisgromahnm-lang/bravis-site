#!/usr/bin/env python3
"""Overlay the owner-approved lunch menu without rebuilding unrelated live pages."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def build(baseline, output):
    if output.exists():
        raise ValueError('Use a new release directory')
    lunch = json.loads((ROOT / 'content/lunch.json').read_text())
    if len(lunch['days']) != 5 or any(len(d['soups']) != 2 or len(d['mains']) != 3 or not d['salad'] for d in lunch['days']):
        raise ValueError('Expected five complete owner-approved daily selections')
    old = (baseline / 'lunch/index.html').read_text()
    source = (ROOT / 'dist/lunch/index.html').read_text()
    mains = re.findall(r'<main\b[^>]*>.*?</main>', source, re.S)
    if len(mains) != 1:
        raise ValueError('Inspect the lunch main region')
    document, count = re.subn(r'<main\b[^>]*>.*?</main>', lambda _: mains[0], old, flags=re.S)
    if count != 1:
        raise ValueError('Inspect the existing lunch main region')
    for attribute in ('name="description"', 'property="og:description"'):
        pattern = r'<meta ' + attribute + r' content="[^"]*">'
        values = re.findall(pattern, source)
        if len(values) != 1:
            raise ValueError('Inspect lunch search description')
        document, count = re.subn(pattern, lambda _: values[0], document)
        if count != 1:
            raise ValueError('Missing original metadata')
    css = (ROOT / 'public/assets/lunch.css').read_bytes()
    digest = hashlib.sha256(css).hexdigest()[:12]
    document, count = re.subn(r'href="/assets/lunch\.css(?:\?v=[a-f0-9]+)?"', f'href="/assets/lunch.css?v={digest}"', document)
    if count != 1:
        raise ValueError('Inspect lunch stylesheet reference')
    target = output / 'lunch/index.html'
    target.parent.mkdir(parents=True)
    target.write_text(document)
    media = [p.relative_to(ROOT / 'public').as_posix() for p in sorted((ROOT / 'public/menu-media').glob('business*')) if re.fullmatch(r'business(?:-[a-z0-9-]+)?\.(?:jpg|pdf)', p.name)]
    for relative in ['assets/lunch.css'] + media:
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'public' / relative, target)
    menu = (baseline / 'menu/index.html').read_text()
    old_images = set(re.findall(r'/menu-media/business(?:-[a-z0-9-]+)?\.jpg', menu))
    if len(old_images) != 1:
        raise ValueError('Inspect current menu gallery before replacing its lunch artwork')
    old_image = old_images.pop()
    target = output / 'menu/index.html'
    target.parent.mkdir(parents=True)
    target.write_text(menu.replace(old_image, lunch['sourceImage']))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.baseline, args.output)
    print('Prepared lunch page, catalogue artwork references, stylesheet and approved JPEG/PDF files')
