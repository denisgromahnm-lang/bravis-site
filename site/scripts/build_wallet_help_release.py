#!/usr/bin/env python3
"""Add wallet help to the card entry points in an existing static release."""
import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from wallet_help import render_wallet_help


def build(baseline, output):
    if output.exists():
        raise ValueError('Use a new output directory')
    css = (ROOT / 'public/assets/wallet-help.css').read_bytes()
    asset = output / 'assets/wallet-help.css'
    asset.parent.mkdir(parents=True)
    asset.write_bytes(css)
    style = '<link rel="stylesheet" href="/assets/wallet-help.css?v=' + hashlib.sha256(css).hexdigest()[:12] + '">'
    files = [baseline / 'index.html', baseline / 'go/index.html', *sorted((baseline / 't').rglob('index.html'))]
    if len(files) != 34:
        raise ValueError('Expected main page, guest hub and 32 table entry pages')
    for source in files:
        original = source.read_text()
        if 'bravis-wallet-help' in original or '/assets/wallet-help.css' in original:
            raise ValueError('Help already exists; inspect the current release')
        route = source.relative_to(baseline)
        if route == Path('index.html'):
            marker = '<span>Откройте камеру телефона и сканируйте QR-код для получения карты гостя.</span></a>'
        elif route == Path('go/index.html'):
            match = re.search(r'<li data-hub-id="guest_card">.*?</a>', original, re.S)
            if not match:
                raise ValueError('Expected existing guest card entry')
            marker = match.group()
        else:
            match = re.search(r'<nav class="table-actions".*?</nav>', original, re.S)
            if not match:
                raise ValueError('Expected existing two-action table entry')
            marker = match.group()
        if original.count(marker) != 1 or original.count('</head>') != 1:
            raise ValueError('Ambiguous insertion point')
        document = original.replace(marker, marker + render_wallet_help(), 1).replace('</head>', style + '</head>', 1)
        # Removing this exact addition must restore every original byte.
        if document.replace(marker + render_wallet_help(), marker, 1).replace(style, '', 1) != original:
            raise ValueError('Existing content changed')
        target = output / route
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(document)
    return len(files)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(f'Added wallet help to {build(args.baseline, args.output)} existing pages; prior content preserved')
