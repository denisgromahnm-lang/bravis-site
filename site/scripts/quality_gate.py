#!/usr/bin/env python3
"""BRAVIS: local, dependency-free quality gates for preview and production safety."""
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT/'dist'
PAGES = ['index.html','menu/index.html','banquets/index.html','contacts/index.html','privacy/index.html']
class Audit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images=[];self.links=[];self.h1=[];self.h2=[]
        self.structured=[];self.jsonld=False;self.capture=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='img':self.images.append(a)
        if tag=='a':self.links.append(a)
        if tag=='h1':self.h1.append(a)
        if tag=='h2':self.h2.append(a)
        if tag=='script' and a.get('type')=='application/ld+json':
            self.jsonld=True;self.capture=[]
    def handle_data(self,data):
        if self.jsonld:self.capture.append(data)
    def handle_endtag(self,tag):
        if tag=='script' and self.jsonld:
            self.structured.append(json.loads(''.join(self.capture)))
            self.jsonld=False
def audit():
    menus=json.loads((ROOT/'content/menu_media.json').read_text(encoding='utf8'))
    assert [x['group'] for x in menus['files']]==['seasonal','main-front','main-back','business','children']
    assert len(menus['files'])==5
    all_urls=[p for menu in menus['files'] for p in menu['pages']]
    assert len(all_urls)==len(set(all_urls)),"Duplicated menu image URL"
    for p in all_urls:
        assert p.startswith('/menu-media/') and p.endswith('.jpg')
        assert (DIST/p.lstrip('/')).is_file(),"Missing menu image "+p
    for p in PAGES:
        content=(DIST/p).read_text(encoding='utf8')
        doc=Audit();doc.feed(content)
        assert len(doc.h1)==1,f"One H1 per page: {p} has {len(doc.h1)}"
        assert len(doc.structured)>=1,"Structured data missing "+p
        assert any(s.get('@type')=='Restaurant' for s in doc.structured),"Restaurant JSON-LD missing "+p
        restaurants=[schema for schema in doc.structured if schema.get('@type')=='Restaurant']
        hours=restaurants[0].get('openingHoursSpecification',{})
        assert hours.get('opens')=='11:00' and hours.get('closes')=='23:00', 'Structured daily hours wrong: '+p
        assert set(hours.get('dayOfWeek',[]))=={'Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'}, 'Missing days of week: '+p
        assert 'Ежедневно, 11:00–23:00' in content,'Display hours missing: '+p
        assert re.search(r'<meta name="robots" content="noindex',content),"Preview accidentally indexable "+p
        assert re.search(r'<meta name="viewport"',content),"Mobile viewport missing "+p
        assert re.search(r'<meta name="description"',content),"SEO description missing "+p
        assert re.search(r'<html lang="ru"',content),"Russian language missing "+p
        for img in doc.images:
            assert img.get('alt') is not None and img.get('alt').strip(),"Missing image alt "+p
            assert img.get('width') and img.get('height'),"Missing dimensions "+p
        for a in doc.links:
            href=a.get('href','')
            assert not href.startswith('http://'),"Insecure hyperlink "+p
            if href.startswith('/'):
                target=DIST/href.split('?',1)[0].split('#',1)[0].lstrip('/')
                if href.endswith('/'):target=target/'index.html'
                assert target.is_file(),f'Broken link {p} -> {href}'
    page=(DIST/'menu/index.html').read_text(encoding='utf8')
    assert page.count('data-menu-index=')==5,"Five menu cards required"
    assert 'id="menu-lightbox"' in page,"Fullscreen accessible menu viewer missing"
    assert 'Бизнес-ланч (комплекс)' in page and 'Детское меню' in page
    assert '.pdf' not in page.lower(),"Direct PDF links are forbidden"
    assert 'Disallow: /' in (DIST/'robots.txt').read_text(encoding='utf8')
    # Essential CSS, JS and images should be cacheable and not huge on mobile.
    assert (DIST/'assets/site.css').stat().st_size < 175000
    assert (DIST/'assets/site.js').stat().st_size < 30000
    for file in (DIST/'uploads').glob('*.jpg'):
        assert file.stat().st_size < 2500000,"Large photo "+file.name
    print('PASS: 5 unique print menus, valid image assets, 5 accessible mobile pages, JSON-LD and noindex')
def test_production_guard():
    config=ROOT/'site.config.json'
    original=config.read_bytes()
    try:
        sample=json.loads(original.decode('utf8'))
        assert sample['public'] is False,'Preview config must not publish by default'
        sample['public']=True
        sample['domain']='https://bravisrest.ru'
        config.write_text(json.dumps(sample,ensure_ascii=False,indent=2),encoding='utf8')
        test=subprocess.run([sys.executable,str(ROOT/'src/build.py')],capture_output=True,text=True,timeout=30)
        assert test.returncode!=0,'FAIL OPEN: public build succeeded with missing credentials'
        assert 'PUBLICATION BLOCKED' in test.stdout+test.stderr,"Unexpected production guard error"
        print('PASS: production build is blocked pending owner verification / activated domain')
    finally:
        config.write_bytes(original)
if __name__=='__main__':
    audit()
    if '--production-guard' in sys.argv:test_production_guard()
