#!/usr/bin/env python3
"""Audit only public Yandex share filenames; identify folders explicitly labelled old food photos."""
from pathlib import Path
import collections, importlib.util, json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('source',ROOT/'scripts/sync_media.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
results={}
for label,share in [('interiors',m.FIRST),('additional',m.SECOND)]:
    files=m.scan(share)
    directories=collections.Counter(str(Path(f.get('path','')).parent) for f in files)
    food=[]
    for f in files:
        path=f.get('path','')
        name=f.get('name','')
        suffix=Path(name).suffix.lower()
        if suffix not in {'.jpg','.jpeg','.webp','.png'}:continue
        p=m.normalize(path)
        old=any(word in p for word in ('стар','old','архив'))
        dish=any(word in p for word in ('еда','блюд','кухн','food','гастрон','съёмк'))
        if old and dish:
            food.append({'name':name,'path':path,'bytes':f.get('size',0)})
    results[label]={
        'folder_sizes':dict(directories.most_common(45)),
        'old_food_candidates':sorted(food,key=lambda x:x['path'])[:140],
        'file_count':len(files)
    }
folder=ROOT/'reports';folder.mkdir(parents=True,exist_ok=True)
(folder/'yandex-food-inventory.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('FOOD PHOTO FOLDER INVENTORY')
for label,entry in results.items():
    print(label,'files',entry['file_count'],'confirmed-old-food-candidates',len(entry['old_food_candidates']))
    for file in entry['old_food_candidates'][:22]:print('  '+file['path'])
print('No photos have been changed or assigned to any dishes.')
