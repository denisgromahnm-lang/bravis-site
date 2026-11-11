#!/usr/bin/env python3
"""Remove a withdrawn loyalty promise without altering the current live release."""
import argparse
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Destinations(HTMLParser):
    def __init__(self, document, *, omit_withdrawn=False):
        super().__init__()
        self.links = []
        self.omit_withdrawn = omit_withdrawn
        self.feed(document)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'a' and 'href' in values:
            if self.omit_withdrawn and values.get('data-track') == 'dessert_invitation_click':
                return
            self.links.append(values['href'])


def build(baseline, output):
    if output.exists():
        raise ValueError('Use a new output directory')
    document = (baseline / 'index.html').read_text()
    source = (ROOT / 'dist/index.html').read_text()
    before = document
    patterns = [r'<aside class="bravis-welcome"[^>]*>.*?</aside>',
                r'<section\b[^>]*\bid="offers"[^>]*>.*?</section>',
                r'<section\b[^>]*\bid="loyalty"[^>]*>.*?</section>']
    for pattern in patterns:
        fragments = re.findall(pattern, source, re.S)
        if len(fragments) != 1:
            raise ValueError('Ambiguous reviewed loyalty section')
        document, count = re.subn(pattern, lambda _: fragments[0], document, flags=re.S)
        if count != 1:
            raise ValueError('Inspect the current loyalty section before updating')
    if before.count('data-track="dessert_invitation_click"') != 1 or 'dessert_invitation_click' in document:
        raise ValueError('Expected exactly the withdrawn dessert contact to be removed')
    if Destinations(before, omit_withdrawn=True).links != Destinations(document).links:
        raise ValueError('All other guest destinations must remain identical')
    target = output / 'index.html'
    target.parent.mkdir(parents=True)
    target.write_text(document)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.baseline, args.output)
    print('Prepared only the home loyalty copy; removed one withdrawn contact, retained all other destinations')
