#!/usr/bin/env python3
"""Build approved production output without modifying the noindex preview."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'production-dist'
config = json.loads((ROOT / 'site.production.json').read_text(encoding='utf-8'))
assert config['domain'] == 'https://bravisrest.ru'
assert all(config.get(key) is True for key in (
    'public', 'menuPricesApproved', 'legalPolicyApproved', 'productionReleaseApproved'))
assert config['operatorContactEmail'] == 'bravis.msk@mail.ru', 'Keep tested official contact until mail migration is approved'
with tempfile.TemporaryDirectory(prefix='bravis-production-') as tmp:
    stage = Path(tmp) / 'site'
    shutil.copytree(ROOT, stage, ignore=shutil.ignore_patterns('dist', 'production-dist', '__pycache__'))
    (stage / 'site.config.json').write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    for script in ('scripts/check_launch_readiness.py', 'src/build.py', 'scripts/render_menu_gallery.py', 'verify.py'):
        args = [sys.executable, str(stage / script)]
        if script.endswith('check_launch_readiness.py'):
            args.append('--strict')
        subprocess.run(args, check=True)
    dist = stage / 'dist'
    routes = ('/', '/menu/', '/banquets/', '/contacts/', '/privacy/')
    for route in routes:
        page = (dist / route.lstrip('/') / 'index.html').read_text(encoding='utf-8')
        assert 'name="robots" content="index, follow' in page, route
        assert f'rel="canonical" href="https://bravisrest.ru{route}"' in page, route
        assert 'content="99ba84ca49429639"' in page, route
        assert 'name="robots" content="noindex' not in page, route
    robots = (dist / 'robots.txt').read_text(encoding='utf-8')
    assert '\nDisallow: /\n' not in '\n' + robots
    assert 'Sitemap: https://bravisrest.ru/sitemap.xml' in robots
    ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    urls = ElementTree.parse(dist / 'sitemap.xml').findall('s:url/s:loc', ns)
    assert {x.text for x in urls} == {'https://bravisrest.ru' + route for route in routes}
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    shutil.copytree(dist, OUTPUT)
print('PASS: production pages, canonical URLs, sitemap, robots and verification tag')
print('Production output:', OUTPUT)
