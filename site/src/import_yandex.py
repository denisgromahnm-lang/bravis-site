#!/usr/bin/env python3
"""Import public BRAVIS images from Yandex Disk without login, OAuth, pip or npm.

Uses the official Yandex Disk public REST API. Downloads ONLY selected still photos
from 'Фото заведения внутри и снаружи', never videos/'Исходники'.
Run: python3 src/import_yandex.py --list
     python3 src/import_yandex.py --download --max 12
Optionally install Pillow to optimize/compress image output automatically.
"""
import argparse
import io
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LINK='https://disk.yandex.ru/d/9up8OtV4hsMOZg'
API='https://cloud-api.yandex.net/v1/disk/public/resources'
IMAGE_EXT={'.jpg','.jpeg','.png','.webp'}


def api_request(path=None, download=False, offset=0):
    params={'public_key':LINK}
    if path:params['path']=path
    if not download:params.update({'limit':100,'offset':offset})
    url=API+('/download' if download else '')+'?'+urllib.parse.urlencode(params)
    request=urllib.request.Request(url,headers={'User-Agent':'BravisSiteImporter/1.0'})
    with urllib.request.urlopen(request,timeout=35) as resp:
        return json.load(resp)


def children(path=None):
    out=[];offset=0
    while True:
        info=api_request(path,offset=offset)
        if info.get('type')!='dir':return []
        embedded=info.get('_embedded',{})
        items=embedded.get('items',[])
        out.extend(items)
        offset+=len(items)
        if not items or offset>=embedded.get('total',len(out)) or offset>=500:break
    return out


def find_photos():
    top=children()
    # Use only the location-specific curated folder; skip the original raws and video archives.
    selected=[x for x in top if x.get('type')=='dir' and 'Фото заведения внутри и снаружи' in x.get('name','')]
    if not selected:
        print('Нужная папка не найдена. Доступные папки:',[x.get('name') for x in top]);return []
    found=[]
    def walk(path,depth=0):
        if depth>5:return
        for item in children(path):
            p=item.get('path','')
            if item.get('type')=='dir':walk(p,depth+1)
            elif item.get('type')=='file':
                n=item.get('name','')
                if Path(n.lower()).suffix in IMAGE_EXT and item.get('size',0) < 14*1024*1024:
                    found.append(item)
    for item in selected:walk(item.get('path'),0)
    # Yandex's order may differ; keep consistent ordering.
    return sorted(found,key=lambda f:f.get('name','').casefold())


def stream_download(url,dest,max_bytes=14*1024*1024):
    req=urllib.request.Request(url,headers={'User-Agent':'BravisSiteImporter/1.0'})
    tmp=dest.with_suffix(dest.suffix+'.part')
    try:
        with urllib.request.urlopen(req,timeout=65) as r, open(tmp,'wb') as f:
            size=0
            while True:
                chunk=r.read(1024*1024)
                if not chunk:break
                size+=len(chunk)
                if size>max_bytes:raise ValueError('Фото слишком большое, пропущено (>14 МБ)')
                f.write(chunk)
        tmp.replace(dest)
    finally:
        if tmp.exists():tmp.unlink()


def optimize(path):
    try:
        from PIL import Image,ImageOps
    except ImportError:
        return path
    try:
        with Image.open(path) as image:
            image=ImageOps.exif_transpose(image)
            image.thumbnail((1920,1920))
            new_path=path.with_suffix('.webp')
            image.convert('RGB').save(new_path,'WEBP',quality=83,method=5)
        path.unlink()
        return new_path
    except Exception as err:
        print('   оптимизация недоступна:',str(err)[:90]);return path


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--list',action='store_true',help='only list filenames, do not download')
    p.add_argument('--download',action='store_true',help='download a small curated subset')
    p.add_argument('--max',type=int,default=12,help='max files to download (default: 12)')
    opts=p.parse_args()
    if opts.max>20 or opts.max<1:p.error('--max must be 1..20')
    try:photos=find_photos()
    except Exception as err:
        print('Yandex Disk API недоступен:',str(err));return 1
    if not photos:
        print('Нет доступных JPEG/PNG/WebP фото в папке.');return 2
    print('Найдено фотографий:',len(photos))
    for row in photos[:40]:print(' -',row.get('name'),round(row.get('size',0)/1024/1024,1),'МБ')
    if not opts.download:
        print('Для загрузки: python3 src/import_yandex.py --download --max 12');return 0
    dest=ROOT/'public/uploads';dest.mkdir(parents=True,exist_ok=True)
    paths=[]
    for ix,item in enumerate(photos[:opts.max],1):
        ext=Path(item.get('name','')).suffix.lower()
        filename=f'bravis-{ix:02d}{ext}'
        target=dest/filename
        try:
            if not target.exists():
                link=api_request(item.get('path'),download=True).get('href')
                if not link:raise ValueError('Missing download href')
                stream_download(link,target)
            final=optimize(target)
            paths.append('/uploads/'+final.name)
            print('Готово:',final.name)
        except Exception as err:
            print('Пропуск',filename,':',str(err)[:150])
    if not paths:
        print('Не удалось загрузить фотографии; проект продолжает работать с иллюстрациями.');return 3
    manifest={'hero':paths[0],'interior':paths[1] if len(paths)>1 else paths[0],
              'food':'', # Do not pass off interior photos as photographs of dishes.
              'events':paths[2] if len(paths)>2 else paths[0],
              'gallery':paths[3:12] if len(paths)>5 else paths[:3]}
    (ROOT/'content/gallery.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Галерея:',ROOT/'content/gallery.json')
    print('Проверьте подбор фотографий и запустите: python3 src/build.py')
    return 0

if __name__=='__main__':sys.exit(main())
