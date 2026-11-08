#!/usr/bin/env python3
"""Add QR landing pages to an existing release without changing its public pages."""
from pathlib import Path
import argparse
import hashlib
import html
import json
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from table_hub import verified_tables, render_table_hub

def build(baseline, output):
    baseline, output = Path(baseline), Path(output)
    if output.exists():
        raise ValueError('Use a new output directory')
    config = json.loads((ROOT / 'site.config.json').read_text())
    config.update(json.loads((ROOT / 'production.config.json').read_text()))
    if config['domain'] != 'https://bravisrest.ru':
        raise ValueError('Use the owner-confirmed restaurant domain')
    tables = verified_tables(json.loads((ROOT / 'content/table-links.json').read_text()))
    document = (baseline / 'index.html').read_text()
    match = re.search(r'\A<!doctype html><html[^>]*><head>(.*?)</head>', document, re.S | re.I)
    if not match:
        raise ValueError('Expected an existing built BRAVIS release')
    metadata = match.group(1)
    metadata = re.sub(r'<link[^>]+rel="canonical"[^>]*>|<meta[^>]+property="og:url"[^>]*>', '', metadata)
    metadata = re.sub(r'<meta name="robots"[^>]*>', '<meta name="robots" content="noindex, nofollow">', metadata)
    metadata = re.sub(r'<title>.*?</title>', '<title>Заказ со стола и карта гостя | BRAVIS</title>', metadata, flags=re.S)
    metadata = re.sub(r'<meta name="description"[^>]*>', '<meta name="description" content="Бизнес-ланч и карта гостя BRAVIS.">', metadata)
    output.mkdir(parents=True)
    (output / 'assets').mkdir()
    shutil.copy(ROOT / 'public/assets/table-hub.css', output / 'assets/table-hub.css')
    for table in [None] + tables:
        route = '/t/' + (table['id'] + '/' if table else '')
        page = render_table_hub(config, '<!doctype html><html lang="ru"><head>' + metadata + '</head><body class="table-page">', table)
        def version(match):
            path = match.group(2)
            asset = output / path.lstrip('/')
            if not asset.exists():
                asset = baseline / path.lstrip('/')
            digest = hashlib.sha256(asset.read_bytes()).hexdigest()[:12]
            return match.group(1) + path + '?v=' + digest + match.group(3)
        page = re.sub(r'((?:href|src)=")(/assets/[A-Za-z0-9_./-]+\.(?:css|js))(?:\?v=[a-f0-9]+)?(")', version, page)
        target = output / route.lstrip('/') / 'index.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page)
    return tables

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    tables = build(args.baseline, args.output)
    print(f'Prepared {len(tables)} verified table pages, safe fallback and one stylesheet; baseline unchanged')
