#!/usr/bin/env python3
"""Publish the reviewed navigation fix on an existing BRAVIS release."""
import argparse
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(baseline, output):
    if output.exists():
        raise ValueError('Use a new output directory')
    menu = baseline / 'menu/index.html'
    old_heading = '<div class="menu-structured-heading"><h2>Блюда, напитки и цены из печатного меню</h2><p>Выбор позиций ниже. Полный ассортимент — на изображениях меню выше.</p></div>'
    if menu.read_text().count(old_heading) != 1:
        raise ValueError('Inspect the current menu before applying this release')
    hashes = {}
    for name in ('site.css', 'site.js'):
        content = (ROOT / 'public/assets' / name).read_bytes()
        target = output / 'assets' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        hashes[name] = hashlib.sha256(content).hexdigest()[:12]
    changed = []
    for source in sorted(baseline.rglob('*.html')):
        original = source.read_text()
        document = original
        if source == menu:
            document = document.replace(old_heading, '<div class="menu-structured-heading"><h2>Блюда и напитки</h2></div>')
            document = document.replace('<p>Названия, цены и объёмы из печатной барной карты ресторана.</p>', '')
            document = document.replace(' · Из печатной барной карты BRAVIS.', '')
        def version(match):
            return match.group(1) + '?v=' + hashes[match.group(2)] + match.group(3)
        document = re.sub(r'((?:href|src)="/assets/(site\.(?:css|js)))(?:\?v=[a-f0-9]+)?(")', version, document)
        if document != original:
            relative = source.relative_to(baseline)
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(document)
            changed.append(str(relative))
    if not changed:
        raise ValueError('No HTML entry points updated')
    return changed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(f'Prepared reviewed CSS/JS and {len(build(args.baseline, args.output))} HTML entry points; QR files unchanged')
