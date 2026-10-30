#!/usr/bin/env python3
"""Build the existing, owner-approved Timeweb site without changing preview settings."""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
output = args.output.resolve()
if output.exists():
    raise SystemExit('Output must be a new directory; existing releases are not overwritten')

with tempfile.TemporaryDirectory(prefix='bravis-release-') as temporary:
    source = Path(temporary) / 'site'
    shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns('dist', 'browser-report', '__pycache__', '.menu-backups'))
    config = json.loads((source / 'site.config.json').read_text(encoding='utf-8'))
    overlay = json.loads((source / 'production.config.json').read_text(encoding='utf-8'))
    config.update(overlay)
    (source / 'site.config.json').write_text(json.dumps(config, ensure_ascii=False), encoding='utf-8')
    for script in ['src/build.py', 'scripts/render_menu_gallery.py', 'verify.py']:
        subprocess.run([sys.executable, str(source / script)], cwd=source, check=True)

    dist = source / 'dist'
    for route in ['index.html', 'menu/index.html', 'lunch/index.html', 'banquets/index.html', 'events/index.html', 'gallery/index.html', 'contacts/index.html', 'privacy/index.html', 'go/index.html']:
        text = (dist / route).read_text(encoding='utf-8')
        path = '/' if route == 'index.html' else '/' + route.removesuffix('index.html')
        assert 'content="index, follow, max-image-preview:large"' in text, route
        assert f'<link rel="canonical" href="https://bravisrest.ru{path}">' in text, route
        assert 'name="yandex-verification" content="99ba84ca49429639"' in text, route
    assert 'https://bravisrest.ru/lunch/' in (dist / 'sitemap.xml').read_text(encoding='utf-8')
    assert 'Allow: /' in (dist / 'robots.txt').read_text(encoding='utf-8')
    shutil.copytree(dist, output)
print('Timeweb release ready:', output)
