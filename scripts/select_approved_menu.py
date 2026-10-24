#!/usr/bin/env python3
"""BRAVIS: install ONLY owner's selected print menus from public Yandex Disk."""
import argparse, datetime, importlib.util, json, re, shutil, sys, tempfile, unicodedata
from pathlib import Path
ROOT=Path("/home/a4dev/bravis-ready")
SOURCE=Path(__file__).with_name("import_additional_media.py")
SELECTION=[
 ("seasonal","Сезонное меню"),
 ("main-front","Основное меню — лицевая сторона"),
 ("main-back","Основное меню — оборот"),
 ("business","Бизнес-ланч"),
 ("children","Детское меню")
]
def norm(s):
    s=unicodedata.normalize("NFKC",str(s)).lower().replace("ё","е")
    return re.sub(r"[\s_\-\u2013\u2014.]+","",s)
def matches(f,k):
    name=str(f.get("name",""))
    ext=Path(name.lower()).suffix
    n=norm(Path(name).stem)
    if k=="seasonal":return ext in (".jpg",".jpeg") and "bravis" in n and "сезон" in n and "превью" in n
    if k=="children":return ext==".pdf" and n=="менюдетское"
    if k=="main-front":return ext==".pdf" and n.startswith("менюосновное") and ("печат" in n or "чатн" in n) and "(1)" not in name and "цвет" not in n
    if k=="main-back":return ext in (".jpg",".jpeg") and n.startswith("менюосновное") and "оборот" in n
    if k=="business":return ext==".pdf" and "менюбизнес" in n and ("печат" in n or "чатн" in n)
    return False
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--apply",action="store_true")
    args=p.parse_args()
    if not SOURCE.is_file():raise ValueError("Нет импортёра Яндекс Диска")
    spec=importlib.util.spec_from_file_location("media",SOURCE)
    media=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(media)
    files,_,_=media.scan()
    print_files=[f for f in files if "типограф" in norm(f.get("path",""))]
    chosen={}
    for key,title in SELECTION:
        candidates=[f for f in print_files if matches(f,key)]
        if len(candidates)!=1:
            raise ValueError(f"Ожидался ровно 1 файл «{title}», найдено {len(candidates)}: {[f.get('name') for f in candidates]}. Без изменений.")
        chosen[key]=candidates[0]
        print("ВЫБРАНО:",title,"—",candidates[0].get("path",""))
    if not args.apply:
        print("Проверка завершена, сайт не изменён.")
        return
    manifest=ROOT/"content/menu_media.json"
    public=ROOT/"public/menu-media"
    build=ROOT/"src/build.py"
    if not all(p.exists() for p in [manifest,public,build]):
        raise RuntimeError("Проект BRAVIS не найден или ранее импортированное меню отсутствует")
    stage=Path(tempfile.mkdtemp(prefix=".approved-menu-",dir=str(ROOT)))
    backup=ROOT/".menu-backups"/datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    newitems=[]
    try:
        st=stage/"menu-media"
        st.mkdir()
        for key,title in SELECTION:
            item=chosen[key]
            ext=Path(item["name"]).suffix.lower()
            cap=35*1024*1024 if ext==".pdf" else 15*1024*1024
            size=item.get("size",0)
            if not isinstance(size,int) or not 500<size<=cap:
                raise RuntimeError("Недопустимый размер "+item["name"])
            dest=st/(key+ext)
            media.fetch_file(item,dest,cap)
            if dest.stat().st_size<=500:
                raise RuntimeError("Пустой документ "+item["name"])
            newitems.append({"title":title,"url":"/menu-media/"+dest.name,"format":"pdf" if ext==".pdf" else "image"})
        if len(newitems)!=5:raise RuntimeError("Неполное меню")
        backup.mkdir(parents=True)
        shutil.copy2(manifest,backup/"menu_media.json")
        # Move all 24 old auto-imported files OUTSIDE publicly served assets.
        shutil.move(str(public),str(backup/"previous-menu-media"))
        try:
            shutil.move(str(st),str(public))
            manifest.write_text(json.dumps({"source":media.SHARE,"selection":"approved-print-menus","files":newitems},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        except Exception:
            if public.exists():shutil.rmtree(public)
            shutil.move(str(backup/"previous-menu-media"),str(public))
            shutil.copy2(backup/"menu_media.json",manifest)
            raise
        # Never use second-folder/new photos as dish photos.
        gallerypath=ROOT/"content/gallery.json"
        if gallerypath.exists():
            gallery=json.loads(gallerypath.read_text(encoding="utf-8"))
            if str(gallery.get("food","")).startswith("/uploads/bravis-extra-"):
                gallery["food"]=""
                gallerypath.write_text(json.dumps(gallery,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
                print("Из роли фото блюда исключено новое фото.")
        print("ОК: 5 утверждённых файлов, в том числе Меню детское.pdf; .ai исключены.")
        print("Старые версии сохранены вне сайта:",backup)
    finally:
        shutil.rmtree(stage,ignore_errors=True)
if __name__=="__main__":
    try:main()
    except Exception as exc:
        print("СТОП:",exc)
        sys.exit(2)
