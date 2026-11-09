#!/usr/bin/env python3
"""Update the consent-gated goal handler on every existing BRAVIS page."""
import argparse
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(baseline, output):
    if output.exists():
        raise ValueError('Use a new output directory')
    script = (ROOT / 'public/assets/site.js').read_bytes()
    digest = hashlib.sha256(script).hexdigest()[:12]
    target = output / 'assets/site.js'
    target.parent.mkdir(parents=True)
    target.write_bytes(script)
    changed = []
    for source in sorted(baseline.rglob('*.html')):
        old = source.read_text()
        document, count = re.subn(r'(\bsrc="/assets/site\.js)(?:\?v=[a-f0-9]+)?(")',
                                  lambda match: match[1] + '?v=' + digest + match[2], old)
        if count == 0:
            continue
        if count != 1:
            raise ValueError('Expected exactly one shared script: ' + str(source))
        if document != old:
            relative = source.relative_to(baseline)
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(document)
            changed.append(str(relative))
    if len(changed) != 42:
        raise ValueError('Inspect the page inventory before publishing: ' + str(len(changed)))
    return changed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print('Prepared goal handler and script version references in', len(build(args.baseline, args.output)), 'existing HTML pages')
