#!/usr/bin/env python3
"""Report BRAVIS launch blockers without modifying files or credentials."""
import argparse,json,os,re
from html import unescape
from urllib.parse import urlsplit
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
c=json.loads((ROOT/'site.config.json').read_text(encoding='utf8'))
fail=[]
def check(label,test):
    print(('PASS ' if test else 'PENDING ')+label)
    if not test:fail.append(label)
check('Own official domain configured',c.get('domain','').removesuffix('/')=='https://bravisrest.ru')
check('Production indexing explicitly enabled',c.get('public') is True)
check('Owner has approved current printed menu prices',c.get('menuPricesApproved') is True)
check('Owner has approved final privacy policy',c.get('legalPolicyApproved') is True)
check('Owner has explicitly authorized publication',c.get('productionReleaseApproved') is True)
check('Legal entity named',bool(c.get('operatorLegalName','').strip()))
check('Legal data processing email',bool(re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',c.get('operatorContactEmail','').strip())))
check('Real hours verified',bool(c.get('hoursText','').strip() and 'уточняйте' not in c.get('hoursText','').lower()))
check('Real Yandex SmartReserve ID',bool(re.fullmatch(r'[A-Za-z0-9_-]{3,120}',str(c.get('smartReserveId','')))))
check('Yandex Metrika ID',str(c.get('yandexMetrikaId','')).isdigit() and int(c.get('yandexMetrikaId') or 0)>0)
check('Yandex verification token',bool(c.get('verificationYandex','').strip()))
# Google Search Console is useful but optional and must not prevent a Yandex-first launch.
google_ready=bool(c.get('verificationGoogle','').strip())
print(('OPTIONAL READY ' if google_ready else 'OPTIONAL PENDING ')+'Google Search Console verification token')
loona_url=str(c.get('loonaJoinUrl','')).strip()
delivery_url=str(c.get('yandexEdaRestaurantUrl','')).strip()
loona_parts=urlsplit(loona_url)
delivery_parts=urlsplit(delivery_url)
check('Owner-provided Loona signup destination',
      loona_parts.scheme=='https' and loona_parts.hostname=='app.loona.ai' and loona_parts.path=='/4992/create/register')
check('Owner-provided Yandex Eda restaurant destination',
      delivery_parts.scheme=='https' and delivery_parts.hostname=='eda.yandex.ru' and delivery_parts.path=='/r/bravis')
qr=ROOT/'public/assets/loona-register.svg'
check('Loona registration QR is linked to the same destination',
      qr.is_file() and loona_url in unescape(qr.read_text(encoding='utf8')))
media=ROOT/'content/menu_media.json'
if media.exists():
    m=json.loads(media.read_text(encoding='utf8'))
    records=m.get('files',[])
    check('Five approved menu sections', [x.get('group') for x in records]==['seasonal','main-front','main-back','business','children'])
    check('All approved image files present',all((ROOT/'public'/p.lstrip('/')).is_file() for x in records for p in x.get('pages',[])))
else:check('Real owner-approved menu',False)
gallery=ROOT/'content/gallery.json'
if gallery.exists():
    g=json.loads(gallery.read_text(encoding='utf8'))
    check('Own restaurant interior photo',bool(g.get('hero') and (ROOT/'public'/g['hero'].lstrip('/')).is_file()))
else:check('Own restaurant interior photo',False)
print('\nOPEN GATES:',len(fail),'|',', '.join(fail) if fail else 'none')
if argparse.ArgumentParser(add_help=False).parse_known_args()[1]:pass
if '--strict' in os.sys.argv and fail:raise SystemExit(2)
