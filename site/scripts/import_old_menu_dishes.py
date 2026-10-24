#!/usr/bin/env python3
"""Import personally authorized BRAVIS older food photos for exact menu items.

Only explicit dish-to-filename pairs reviewed against the currently displayed
menu are eligible. No fuzzy or generic-category matches, no guessing.
Download authorized public Yandex Disk images, optimize, and add image paths
to the textual menu. Does not edit price fields or publish the official domain.
"""
import hashlib
import importlib.util
import json
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageOps, UnidentifiedImageError

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bravis_media',ROOT/'scripts/sync_media.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
SOURCE_DIR='/Фотографии еды/Старое меню фото'
PHOTO_PREFIX='/uploads/dishes/'

# Mapping reviewed 24.10.2026 against the full Yandex old-menu inventory.
# Exact names or unambiguous equivalent dish names, not other variations.
MATCHES={
  'Армянская сырная тарелка':'хз/армянская сырная тарелка.jpg',
  'Баклажаны и кабачки с ореховым муссом':'хз/баклажаны и кабачки с ореховым муссом.jpg',
  'Кавказская брускетта микс':'хз/кавказская брускетта микс.jpg',
  'Мясная тарелка':'хз/мясная тарелка.jpg',
  'Рыбная тарелка':'хз/рыбная тарелка.jpg',
  'Овощной букет':'хз/овощной букет.jpg',
  'Соленья':'хз/соленья.jpg',
  'Греческий':'салаты/греческий.jpg',
  'Салат с ростбифом':'салаты/ростбиф.jpg',
  'Хрустящий баклажан':'салаты/хрустящий баклажан.jpg',
  'Цезарь с курицей':'салаты/цезарь с курицей.jpg',
  'Куриный бульон с лапшой':'супы/куриный суп-лапша.jpg',
  'Солянка':'супы/солянка.jpg',
  'Суп харчо':'супы/харчо.jpg',
  'Люля из баранины':'мангал/люля из баранины.jpg',
  'Люля из говядины':'мангал/люля из говядины.jpg',
  'Люля из курицы':'мангал/люля из курицы.jpg',
  'Шашлык из бараньей корейки':'мангал/шашлык из бараньей корейки.jpg',
  'Шашлык из бараньей мякоти':'мангал/шашлык из бараньей мякоти.jpg',
  'Шашлык из говяжьей вырезки':'мангал/шашлык из говяжьей вырезки миньон.jpg',
  'Шашлык из курицы':'мангал/шашлык из куриного филе.jpg',
  'Шашлык из свиной шейки':'мангал/шашлык из свиной шейки.jpg',
  'Ламаджо':'выпечка/ламаджо.jpg',
  'Хачапури по-аджарски':'выпечка/хач по аджарски.jpg',
  'Хачапури по-мегрельски':'выпечка/хач по мегрель.jpg',
  'Хачапури по-аджарски, 5 сыров':'выпечка/хач по аджарски 5 сыр.jpg',
  'Хачапури по-мегрельски, 5 сыров':'выпечка/хач по мегр 5 сыров.jpg',
  'Аришта с курицей':'горячие/аришта с курицей.jpg',
  'Толма':'горячие/толма.jpg',
  'Цыплёнок табака':'горячие/цыпленок табака.jpg',
  'Фаршированные грибы':'гз/фаршированные грибы.jpg',
  'Чашушули':'горячие/чашашули.jpg',
  'Бравис':'десерты/бравис.jpg',
  'Гата':'десерты/гата.jpg',
  'Мильфей':'десерты/мильфей.jpg',
}

def main():
    manifest=ROOT/'reports/yandex-food-inventory.json'
    catalog=json.loads(manifest.read_text(encoding='utf8'))
    assert not catalog['errors'] and catalog['photo_count']>=90, 'Yandex inventory incomplete'
    indexed={f['path']:f for f in catalog['photos']}
    menu_path=ROOT/'content/menu.json'
    menu=json.loads(menu_path.read_text(encoding='utf8'))
    dish_map={item['name']:item for section in menu['sections'] for item in section.get('items',[])}
    assert len(dish_map)==sum(len(s.get('items',[])) for s in menu['sections'])
    assert set(MATCHES)<=set(dish_map), 'Mapping references dishes absent from current menu'
    assert len(MATCHES)==len(set(MATCHES.values())), 'One old photo must not map to multiple distinct dishes'
    for dish,relative in MATCHES.items():
        full=SOURCE_DIR+'/'+relative
        assert full in indexed, 'Old food photo missing from inventory: '+full
        assert indexed[full]['size']<=18*1024*1024, 'Oversized image '+full
    out_dir=ROOT/'public/uploads/dishes'
    out_dir.mkdir(parents=True,exist_ok=True)
    results=[]
    imported=0
    with TemporaryDirectory() as folder:
        temporary=Path(folder)
        for i,(name,rel) in enumerate(MATCHES.items(),1):
            source=SOURCE_DIR+'/'+rel
            file=indexed[source]
            short_hash=hashlib.sha256(source.encode('utf8')).hexdigest()[:13]
            dest=out_dir/('bravis-food-'+short_hash+'.jpg')
            url=PHOTO_PREFIX+dest.name
            if dest.exists() and dest.stat().st_size>0:
                dish_map[name]['image']=url
                results.append({'dish':name,'source':source,'url':url,'status':'reused'})
                imported+=1
                continue
            raw=temporary/('raw-'+str(i)+'.jpg')
            error=None
            for attempt in range(3):
                try:
                    m.download(m.SECOND,file,raw,max_size=18*1024*1024)
                    with Image.open(raw) as original:
                        original=ImageOps.exif_transpose(original)
                        original.thumbnail((760,760),Image.Resampling.LANCZOS)
                        if original.width<120 or original.height<120:
                            raise ValueError('Photo has insufficient resolution')
                        original.convert('RGB').save(dest,'JPEG',quality=83,optimize=True,progressive=True)
                    if dest.stat().st_size>1_800_000:
                        raise ValueError('Optimized image unexpectedly large')
                    dish_map[name]['image']=url
                    results.append({'dish':name,'source':source,'url':url,'status':'imported',
                                    'bytes':dest.stat().st_size})
                    imported+=1
                    error=None
                    break
                except (OSError,ValueError,UnidentifiedImageError) as exc:
                    error=str(exc)
                    if dest.exists():dest.unlink()
                    print('IMAGE RETRY',name,attempt+1, error[:160],flush=True)
                    time.sleep(attempt+1)
            if error:
                results.append({'dish':name,'source':source,'status':'unavailable','error':error[:180]})
                print('SKIPPED',name,error[:180],flush=True)
    if imported<1:
        raise RuntimeError('No old menu images were imported, not updating menu')
    # Don't touch prices, recipe descriptions or pre-existing images of other dishes.
    menu['oldMenuPhotoSource']=SOURCE_DIR
    menu_path.write_text(json.dumps(menu,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    report={'catalog':SOURCE_DIR,'sourceShare':m.SECOND,
            'matched':imported,'eligible':len(MATCHES),
            'totalMenuDishes':len(dish_map),
            'images':results,
            'note':'Photos are historical BRAVIS menu photography. Dish variants without precise filename matches remain unillustrated; plating may have changed.'}
    (ROOT/'reports/old-menu-photo-matches.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('IMPORTED OLD PHOTOS',imported,'OF',len(MATCHES),'DISHES',len(dish_map),flush=True)
    for entry in results:print(entry['status'],entry['dish'],entry.get('url',''),flush=True)

if __name__=='__main__': main()
