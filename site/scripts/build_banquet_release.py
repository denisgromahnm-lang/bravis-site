#!/usr/bin/env python3
"""Update the banquet page over the current production release."""
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def one(pattern, document):
    values = re.findall(pattern, document, re.S)
    if len(values) != 1:
        raise ValueError('Inspect the banquet insertion point: ' + pattern)
    return values[0]


def replace(pattern, document, value):
    document, count = re.subn(pattern, lambda _: value, document, flags=re.S)
    if count != 1:
        raise ValueError('Ambiguous banquet replacement: ' + pattern)
    return document


def build(baseline, output):
    if output.exists():
        raise ValueError('Use a new output directory')
    relative = 'banquets/index.html'
    old = (baseline / relative).read_text()
    source = (ROOT / 'dist' / relative).read_text()
    document = replace(r'<main\b[^>]*>.*?</main>', old, one(r'<main\b[^>]*>.*?</main>', source))
    for attribute in ('name="description"', 'property="og:description"'):
        pattern = r'<meta ' + attribute + r' content="[^"]*">'
        document = replace(pattern, document, one(pattern, source))
    style = one(r'<link rel="stylesheet" href="/assets/banquets\.css\?v=[a-f0-9]+">', source)
    if '/assets/banquets.css' in old:
        raise ValueError('Inspect the existing banquet stylesheet before updating it')
    document = document.replace('</head>', style + '</head>', 1)
    if re.findall(r'\bhref="([^"]+)"', one(r'<main\b[^>]*>.*?</main>', old)) != re.findall(r'\bhref="([^"]+)"', one(r'<main\b[^>]*>.*?</main>', document)):
        raise ValueError('Existing banquet destinations must remain identical')
    target = output / relative
    target.parent.mkdir(parents=True)
    target.write_text(document)
    target = output / 'assets/banquets.css'
    target.parent.mkdir()
    target.write_bytes((ROOT / 'public/assets/banquets.css').read_bytes())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.baseline, args.output)
    print('Prepared one banquet page and its stylesheet; existing destinations retained')
