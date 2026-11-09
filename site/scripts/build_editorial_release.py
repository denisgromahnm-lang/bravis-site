#!/usr/bin/env python3
"""Refresh approved editorial regions over the current live BRAVIS release."""
import argparse
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(document, pattern, replacement):
    document, count = re.subn(pattern, lambda _: replacement, document, flags=re.S)
    if count != 1:
        raise ValueError('Inspect the editorial insertion point: ' + pattern)
    return document


def build(baseline, output):
    if output.exists():
        raise ValueError('Use a new output directory')
    dist = ROOT / 'dist'
    script = (ROOT / 'public/assets/restaurant-life.js').read_bytes()
    digest = hashlib.sha256(script).hexdigest()[:12]
    for relative, content in [('assets/restaurant-life.js', script),
                              ('assets/restaurant-life.json', (dist / 'assets/restaurant-life.json').read_bytes())]:
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    for relative in ('index.html', 'events/index.html'):
        source = (dist / relative).read_text()
        document = (baseline / relative).read_text()
        for part in ('today', 'news'):
            pattern = r'<section\b[^>]*\bid="bravis-' + part + r'"[^>]*>.*?</section>'
            fragments = re.findall(pattern, source, re.S)
            if len(fragments) != 1:
                raise ValueError('Ambiguous source editorial section: ' + part)
            document = replace_once(document, pattern, fragments[0])
        pattern = r'<script type="application/json" id="restaurant-life-data">.*?</script>'
        snapshots = re.findall(pattern, source, re.S)
        if len(snapshots) != 1:
            raise ValueError('Editorial snapshot missing')
        document = replace_once(document, pattern, snapshots[0])
        document = replace_once(document, r'\bsrc="/assets/restaurant-life\.js(?:\?v=[a-f0-9]+)?"',
                                f'src="/assets/restaurant-life.js?v={digest}"')
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(document)
    relative = 'lunch/index.html'
    description = re.findall(r'<meta name="description" content="[^"]*">', (dist / relative).read_text())
    if len(description) != 1:
        raise ValueError('Lunch description missing')
    document = replace_once((baseline / relative).read_text(),
                            r'<meta name="description" content="[^"]*">', description[0])
    target = output / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.baseline, args.output)
    print('Prepared current-day/news regions, editorial feed/player-independent script and lunch search description')
