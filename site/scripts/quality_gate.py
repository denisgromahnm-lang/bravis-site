#!/usr/bin/env python3
"""BRAVIS: local, dependency-free quality gates for preview and production safety."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT/'dist'
PAGES = ['index.html','menu/index.html','lunch/index.html','banquets/index.html','contacts/index.html','privacy/index.html','go/index.html','events/index.html','gallery/index.html']
class Audit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images=[];self.links=[];self.h1=[];self.h2=[]
        self.structured=[];self.jsonld=False;self.capture=[]
        self.human_text=[];self.nontext=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ('script','style'):self.nontext+=1
        for name in ('alt','aria-label','title'):
            if a.get(name):self.human_text.append(a[name])
        if tag=='img':self.images.append(a)
        if tag=='a':self.links.append(a)
        if tag=='h1':self.h1.append(a)
        if tag=='h2':self.h2.append(a)
        if tag=='script' and a.get('type')=='application/ld+json':
            self.jsonld=True;self.capture=[]
    def handle_data(self,data):
        if self.jsonld:self.capture.append(data)
        if not self.nontext:self.human_text.append(data)
    def handle_endtag(self,tag):
        if tag=='script' and self.jsonld:
            self.structured.append(json.loads(''.join(self.capture)))
            self.jsonld=False
        if tag in ('script','style'):self.nontext=max(0,self.nontext-1)
def audit():
    menus=json.loads((ROOT/'content/menu_media.json').read_text(encoding='utf8'))
    assert [x['group'] for x in menus['files']]==['seasonal','main-front','main-back','business','children']
    assert len(menus['files'])==5
    assert menus['files'][0].get('published') is False, 'Seasonal source must remain explicitly unpublished'
    published=[menu for menu in menus['files'] if menu.get('published',True)]
    assert [menu['group'] for menu in published]==['main-front','main-back','business','children'], 'Exactly four approved menus must be public'
    all_urls=[p for menu in menus['files'] for p in menu['pages']]
    assert len(all_urls)==len(set(all_urls)),"Duplicated menu image URL"
    for menu in menus['files']:
        for p in menu['pages']:
            assert p.startswith('/menu-media/') and p.endswith('.jpg')
            assert (ROOT/'public'/p.lstrip('/')).is_file(), 'Approved source was lost: '+p
            if menu.get('published',True):
                assert (DIST/p.lstrip('/')).is_file(),"Missing published menu image "+p
            else:
                assert not (DIST/p.lstrip('/')).exists(), 'Inactive artwork must not be distributed: '+p
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
        if p!='go/index.html':
            assert 'Ежедневно, 11:00–23:00' in content,'Display hours missing: '+p
        assert re.search(r'<meta name="robots" content="noindex',content),"Preview accidentally indexable "+p
        assert re.search(r'<meta name="viewport"',content),"Mobile viewport missing "+p
        assert re.search(r'<meta name="description"',content),"SEO description missing "+p
        assert re.search(r'<html lang="ru"',content),"Russian language missing "+p
        if p!='privacy/index.html':
            assert not re.search(r'loona|luna|луна', ' '.join(doc.human_text), re.I), 'Provider brand leaked into guest marketing: '+p
        for img in doc.images:
            assert img.get('alt') is not None and img.get('alt').strip(),"Missing image alt "+p
            assert img.get('width') and img.get('height'),"Missing dimensions "+p
        for a in doc.links:
            href=a.get('href','')
            assert not href.startswith('http://'),"Insecure hyperlink "+p
            if href.startswith('/'):
                # Resolve URL path independently of query and hash; "/#delivery"
                # points to the root HTML document, not an empty directory.
                path_part=href.split('?',1)[0].split('#',1)[0]
                target=DIST/path_part.lstrip('/')
                if path_part.endswith('/'):target=target/'index.html'
                assert target.is_file(),f'Broken link {p} -> {href}'
                if href=='/#delivery':
                    assert 'id="delivery"' in (DIST/'index.html').read_text(encoding='utf8'), 'Delivery anchor missing'
    page=(DIST/'menu/index.html').read_text(encoding='utf8')
    assert page.count('data-menu-index=')==4,"Four published menu cards required"
    payload=re.search(r'<script type="application/json" id="bravis-menu-data">(.*?)</script>',page,re.S)
    assert payload, 'Menu viewer payload missing'
    viewer=json.loads(payload.group(1))
    assert [item['pages'] for item in viewer]==[item['pages'] for item in published], 'Viewer must expose exactly the published original images'
    menu_doc=Audit();menu_doc.feed(page)
    menu_schemas=[item for item in menu_doc.structured if item.get('@type')=='Menu']
    assert len(menu_schemas)==1, 'One public menu schema is required'
    assert [item['name'] for item in menu_schemas[0]['hasMenuSection']]==[item['title'] for item in published], 'Menu schema exposed an unpublished section'
    assert '/menu-media/seasonal.jpg' not in page and 'id="seasonal-dishes"' not in page, 'Hidden seasonal menu leaked into the public page'
    assert 'id="menu-lightbox"' in page,"Fullscreen accessible menu viewer missing"
    assert 'Бизнес-ланч (комплекс)' in page and 'Детское меню' in page
    assert '.pdf' not in page.lower(),"Direct PDF links are forbidden"
    assert 'Disallow: /' in (DIST/'robots.txt').read_text(encoding='utf8')
    # Essential CSS, JS and images should be cacheable and not huge on mobile.
    assert (DIST/'assets/site.css').stat().st_size < 175000
    assert (DIST/'assets/site.js').stat().st_size < 30000
    for file in (DIST/'uploads').glob('*.jpg'):
        assert file.stat().st_size < 2500000,"Large photo "+file.name
    print('PASS: five preserved sources, four published menus, nine mobile pages, guest brand, JSON-LD and noindex')
def test_production_guard():
    # A negative build must not overwrite another worker's shared configuration.
    with tempfile.TemporaryDirectory(prefix='bravis-production-guard-') as temporary:
        source=Path(temporary)/'site'
        shutil.copytree(ROOT,source,ignore=shutil.ignore_patterns('dist','browser-report','__pycache__','.menu-backups'))
        config=source/'site.config.json'
        sample=json.loads(config.read_text(encoding='utf8'))
        assert sample['public'] is False,'Preview config must not publish by default'
        sample['public']=True
        sample['domain']='https://bravisrest.ru'
        config.write_text(json.dumps(sample,ensure_ascii=False,indent=2),encoding='utf8')
        test=subprocess.run([sys.executable,str(source/'src/build.py')],capture_output=True,text=True,timeout=30,cwd=source)
        assert test.returncode!=0,'FAIL OPEN: public build succeeded with missing credentials'
        assert 'PUBLICATION BLOCKED' in test.stdout+test.stderr,"Unexpected production guard error"
        print('PASS: production build is blocked pending owner verification / activated domain')
if __name__=='__main__':
    audit()
    if '--production-guard' in sys.argv:test_production_guard()
