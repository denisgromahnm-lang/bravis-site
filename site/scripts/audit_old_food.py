#!/usr/bin/env python3
"""Catalog all files in the owner-provided old-menu food folder (public Yandex Disk).

Metadata only; does not publish images or guess which dishes they depict.
Used to prepare a manual match of dish names and filenames.
"""
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('source',ROOT/'scripts/sync_media.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

FOLDER='/Фотографии еды/Старое меню фото'
IMAGE_EXT={'.jpg','.jpeg','.png','.webp','.heic'}
out=[]
fail=[]
queue=[FOLDER]
while queue:
    folder=queue.pop(0)
    offset=0
    try:
        while True:
            response=m.req(m.SECOND,path=folder,offset=offset)
            if response.get('type')!='dir':
                raise ValueError('Expected directory: '+folder)
            embedded=response.get('_embedded',{})
            items=embedded.get('items',[])
            for item in items:
                name=item.get('name','')
                path=item.get('path','')
                if item.get('type')=='dir':
                    queue.append(path)
                elif item.get('type')=='file' and Path(name).suffix.lower() in IMAGE_EXT:
                    out.append({'name':name,'path':path,'size':item.get('size',0),
                                'mime_type':item.get('mime_type','')})
            offset+=len(items)
            if not items or offset>=embedded.get('total',offset):
                break
    except Exception as exc:
        fail.append({'folder':folder,'error':str(exc)[:250]})
        print('SCAN WARNING',folder,str(exc)[:180])
result={'source':'Second BRAVIS owner-shared Yandex Disk','share':m.SECOND,
        'folder':FOLDER,'photos':sorted(out,key=lambda f:f['path'].casefold()),
        'photo_count':len(out),'errors':fail}
target=ROOT/'reports/yandex-food-inventory.json'
target.parent.mkdir(parents=True,exist_ok=True)
target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Old menu photos:',len(out),'errors:',len(fail))
for file in out:
    print('OLD FOOD:',file['path'], 'bytes',file['size'])
if fail or not out:
    raise SystemExit('Cannot confidently inventory old food photos.')
