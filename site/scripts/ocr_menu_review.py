#!/usr/bin/env python3
"""Extract review-only OCR text from the five owner-approved BRAVIS menu images.
Does not publish OCR as menu prices. Requires tesseract with rus and eng data.
"""
import json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
m=json.loads((ROOT/'content/menu_media.json').read_text(encoding='utf8'))
assert m.get('selection')=='owner-approved-print-menu'
dest=ROOT/'content/menu-ocr-review';dest.mkdir(parents=True,exist_ok=True)
for item in m['files']:
    name=item['group']
    path=ROOT/'public'/item['url'].lstrip('/')
    assert path.is_file(),path
    psm='6' if name in ('business','children','seasonal') else '11'
    run=subprocess.run(['tesseract',str(path),'stdout','-l','rus+eng','--psm',psm],
       stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=180)
    if run.returncode:raise RuntimeError('OCR failed '+name+': '+run.stderr[-500:])
    text=run.stdout.strip()
    (dest/(name+'.txt')).write_text(text+'\n',encoding='utf8')
    print('OCR REVIEW ONLY',name,len(text),'characters;',len(text.splitlines()),'lines')
print('Output is a DRAFT; do not publish without checking against original PDF/JPG.')
