#!/usr/bin/env python3
"""Add reviewed restaurant videos to the current BRAVIS release."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from event_media import ARROW, render_restaurant_videos


def build(baseline, output):
    if output.exists():
        raise ValueError('Use a new output directory')
    data = json.loads((ROOT / 'content/event-media.json').read_text())
    video_html = render_restaurant_videos(data)
    if not video_html or len(data['videos']) != 2:
        raise ValueError('Expected the two reviewed restaurant clips')
    sources = ['assets/event-media.css'] + [v[key].lstrip('/') for v in data['videos'] for key in ('src', 'poster')]
    for relative in sources:
        source = ROOT / 'public' / relative
        target = output / relative
        if (baseline / relative).exists():
            raise ValueError('Inspect the existing asset before replacing it: ' + relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    digest = hashlib.sha256((output / 'assets/event-media.css').read_bytes()).hexdigest()[:12]
    style = f'<link rel="stylesheet" href="/assets/event-media.css?v={digest}">'
    for relative in ('index.html', 'events/index.html', 'gallery/index.html'):
        document = (baseline / relative).read_text()
        if 'id="bravis-in-motion"' in document:
            raise ValueError('Video block already present')
        if relative == 'index.html':
            marker = '<p>Каждая встреча — своя история. А место для неё уже есть.</p>'
            replacement = ('<p>Каждая встреча — своя история. А место для неё уже есть.<br>'
                           f'<a class="text-link" href="/gallery/">Посмотреть фото и видео {ARROW}</a></p>')
        elif relative == 'events/index.html':
            marker = '<section class="section restaurant-life restaurant-life--formats"'
            replacement = video_html + marker
            # The native clips replace the previous external archive-video link.
            document, count = re.subn(r'<a class="text-link" href="https://rutube\.ru/video/c2c357acb4f02a17b8ac298d603e38be/"[^>]*>.*?</a><p class="subtle">Архивный сюжет о ресторане\. Фотографии выше показывают интерьер, а не съёмки фильма\.</p>', '', document)
            if count != 1:
                raise ValueError('Inspect the archive-video entry before replacing it')
        else:
            marker = '<section class="restaurant-gallery"'
            replacement = video_html + marker
        if document.count(marker) != 1:
            raise ValueError('Ambiguous page insertion point: ' + relative)
        document = document.replace(marker, replacement, 1)
        if relative != 'index.html':
            if '/assets/event-media.css' in document:
                raise ValueError('Inspect the existing video stylesheet')
            document = document.replace('</head>', style + '</head>', 1)
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(document)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.baseline, args.output)
    print('Prepared two clips, two posters, one stylesheet and three existing pages; table routes unchanged')
