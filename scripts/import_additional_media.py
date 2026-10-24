#!/usr/bin/env python3
"""BRAVIS: safely import additional public Yandex Disk assets into preview only.

Usage: python3 scripts/import_additional_media.py --list
       python3 scripts/import_additional_media.py --apply
No pip, npm, OAuth or browser upload needed. Never enables production indexing.
"""
import argparse
import hashlib
import html
import json
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

SHARE = "https://disk.yandex.ru/d/mM7bPzFGD0o2WA"
ENDPOINT = "https://cloud-api.yandex.net/v1/disk/public/resources"
ROOT = Path("/home/a4dev/bravis-ready")
IMAGES = {".jpg", ".jpeg", ".png", ".webp"}
MENU_FILES = IMAGES | {".pdf"}
IGNORE = ("исходник", "оригинал", "raw", "архив", "archive", "backup", "video", "видео", ".psd", "макет")
MENU_WORDS = ("меню", "menu", "винная карта", "карта напитков", "барная карта", "wine list", "food menu", "менюш")
IMAGE_MAX, PDF_MAX, TOTAL_MAX = 15 * 1024**2, 35 * 1024**2, 140 * 1024**2
HEADERS = {"User-Agent": "BRAVIS-site-public-media-importer/1.0"}

def req(path=None, download=False, offset=0):
    query = {"public_key": SHARE}
    if path is not None:
        query["path"] = path
    if not download:
        query.update({"limit": 100, "offset": offset})
    url = ENDPOINT + ("/download" if download else "") + "?" + urllib.parse.urlencode(query)
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=35) as f:
        return json.load(f)

def scan():
    queue = [(None, 0)]
    files, dirs, requests = [], 0, 0
    while queue and requests < 120 and len(files) < 2000:
        path, depth = queue.pop(0)
        if depth > 7:
            continue
        offset = 0
        while requests < 120:
            result = req(path=path, offset=offset)
            requests += 1
            if result.get("type") == "file":
                files.append(result)
                break
            if result.get("type") != "dir":
                break
            embedded = result.get("_embedded", {})
            items = embedded.get("items", [])
            for item in items:
                label = (item.get("path") or item.get("name") or "").lower()
                if item.get("type") == "dir":
                    if any(w in label for w in IGNORE):
                        continue
                    queue.append((item.get("path"), depth + 1))
                    dirs += 1
                elif item.get("type") == "file":
                    files.append(item)
            offset += len(items)
            if not items or offset >= embedded.get("total", offset) or len(files) >= 2000:
                break
    return files, dirs, requests

def classify(item):
    name = item.get("name", "")
    full = item.get("path", "") or name
    lower = full.lower()
    ext = Path(name.lower()).suffix
    size = item.get("size", 0)
    if not isinstance(size, int) or size <= 0:
        return "skip"
    if any(w in lower for w in IGNORE) or ext not in MENU_FILES:
        return "skip"
    is_menu = any(w in lower for w in MENU_WORDS)
    if is_menu and ext in MENU_FILES and size <= (PDF_MAX if ext == ".pdf" else IMAGE_MAX):
        return "menu"
    if ext in IMAGES and size <= IMAGE_MAX:
        return "photo"
    return "skip"

def description(items):
    for item in items[:50]:
        print(" -", ("[МЕНЮ]" if classify(item) == "menu" else "[ФОТО]"),
              item.get("name", "?")[:75], f'{item.get("size", 0)/1024**2:.1f} MB',
              (item.get("path", "") or "")[:90])

def safe_name(prefix, idx, ext):
    return f"bravis-extra-{prefix}-{idx:03d}{ext}"

def fetch_file(item, dest, max_bytes):
    info = req(item.get("path"), download=True)
    href = info.get("href", "")
    parsed = urllib.parse.urlsplit(href)
    host = parsed.hostname or ""
    if parsed.scheme != "https" or not host.endswith((".yandex.ru", ".yandex.net", ".yandex.com")):
        raise ValueError("Неожиданный адрес для скачивания; загрузка запрещена")
    tmp = dest.with_name(dest.name + ".part")
    try:
        with urllib.request.urlopen(urllib.request.Request(href, headers=HEADERS), timeout=70) as r, tmp.open("wb") as output:
            used = 0
            while True:
                data = r.read(1024 * 1024)
                if not data:
                    break
                used += len(data)
                if used > max_bytes:
                    raise ValueError("Файл превышает разрешённый размер")
                output.write(data)
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)

def optimize_image(path):
    try:
        from PIL import Image, ImageOps
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)
            im.thumbnail((1920, 1920))
            dest = path.with_suffix(".webp")
            im.convert("RGB").save(dest, "WEBP", quality=82, method=5)
            if dest != path:
                path.unlink()
            return dest
    except ImportError:
        return path
    except Exception as e:
        print("  Фото сохранено без оптимизации:", str(e)[:100])
        return path

def inject_menu_gallery(builder):
    source = builder.read_text(encoding="utf-8")
    if "BRAVIS_ADDITIONAL_MENU_GALLERY_V1" in source:
        return False
    marker = "menu_top+=f'''<div class=\"menu-bottom-note\">"
    if marker not in source:
        raise RuntimeError("Версия шаблона изменилась: точка вставки меню не найдена")
    # Suppress the 'coming soon' panel only when verified menu media is present.
    source = source.replace(
        "else:\n    menu_top+=f'''<div class=\"menu-placeholder\">",
        "elif not MENU_MEDIA:\n    menu_top+=f'''<div class=\"menu-placeholder\">",
        1
    )
    gallery_code = '''
# BRAVIS_ADDITIONAL_MENU_GALLERY_V1: original menu pages, not invented items or prices
if MENU_MEDIA:
    menu_top += '<section class="menu-scans" aria-label="Оригинальные страницы меню"><div class="menu-scans-head"><h2>Посмотреть меню</h2><p>Оригинальные страницы меню ресторана. Наличие, состав и стоимость уточняйте у сотрудников.</p></div><div class="menu-scans-grid">'
    for ix, media in enumerate(MENU_MEDIA[:30], 1):
        href = h(media.get("url", ""))
        if not href.startswith("/menu-media/"):
            continue
        fmt = media.get("format", "")
        if fmt == "pdf":
            menu_top += f'<a class="menu-sheet menu-sheet--pdf" href="{href}" target="_blank" rel="noopener"><span class="menu-sheet__icon">PDF</span><strong>{h(media.get("title", "Меню в PDF"))}</strong><span>Открыть документ ↗</span></a>'
        else:
            menu_top += f'<a class="menu-sheet" href="{href}" target="_blank" rel="noopener"><img src="{href}" alt="Страница меню BRAVIS №{ix}: {h(media.get("title", ""))}" width="420" height="590" loading="lazy"><strong>{h(media.get("title", "Страница меню"))}</strong><span>Открыть крупно ↗</span></a>'
    menu_top += '</div></section>'
'''
    source = source.replace(marker, gallery_code + "\n" + marker, 1)
    marker2 = "GALLERY = json.loads((ROOT / 'content/gallery.json')"
    insert2 = "MENU_MEDIA = json.loads((ROOT / 'content/menu_media.json').read_text(encoding='utf-8')).get('files', []) if (ROOT / 'content/menu_media.json').exists() else []\n"
    if marker2 not in source:
        raise RuntimeError("Версия шаблона изменилась: точка чтения JSON не найдена")
    source = source.replace(marker2, insert2 + marker2, 1)
    builder.write_text(source, encoding="utf-8")
    return True

STYLE = """
/* BRAVIS additional original menu pages */
.menu-scans{margin:64px 0 12px;padding-top:35px;border-top:1px solid #cdbcae}
.menu-scans-head h2{font-size:clamp(30px,4.5vw,52px);font-weight:400;line-height:1.1;margin:0 0 12px}
.menu-scans-head p{max-width:640px;color:#66595c;margin:0 0 28px}
.menu-scans-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(205px,1fr));gap:22px}
.menu-sheet{display:flex;flex-direction:column;gap:10px;color:#302229;text-decoration:none;padding:12px;background:#fffaf4;border:1px solid #d9c7b8;transition:transform .2s,box-shadow .2s}
.menu-sheet:hover{transform:translateY(-3px);box-shadow:0 8px 24px #31202418}
.menu-sheet img{display:block;width:100%;height:auto;aspect-ratio:3/4;object-fit:contain;background:#efe6dc}
.menu-sheet strong{font-size:17px;font-weight:500;overflow-wrap:anywhere}
.menu-sheet span{font-size:12px;letter-spacing:.06em}
.menu-sheet--pdf{justify-content:center;align-items:center;min-height:280px;text-align:center}
.menu-sheet__icon{font-size:42px!important;color:#874758;font-weight:700}
"""

def apply(photos, menus):
    required = [ROOT / "src/build.py", ROOT / "content/gallery.json", ROOT / "public/assets/site.css", ROOT / "install-preview.sh"]
    if not all(p.is_file() for p in required):
        raise RuntimeError("Не найден существующий BRAVIS-проект по адресу " + str(ROOT))
    if not (Path("/home/a4dev/bravis-site/dist/index.html")).is_file():
        raise RuntimeError("Не найден существующий предпросмотр; установка запрещена")

    photo_dest = ROOT / "public/uploads"
    menu_dest = ROOT / "public/menu-media"
    photo_dest.mkdir(parents=True, exist_ok=True)
    menu_dest.mkdir(parents=True, exist_ok=True)
    downloaded_photos, downloaded_menus, cumulative = [], [], 0
    for kind, subset, dst, prefix in (
        ("photo", photos[:14], photo_dest, "photo"),
        ("menu", menus[:24], menu_dest, "menu")
    ):
        for ix, item in enumerate(subset, 1):
            size = item.get("size", 0)
            if cumulative + size > TOTAL_MAX:
                print("Лимит загрузки 140MB: оставшиеся файлы пропущены")
                break
            ext = Path(item.get("name", "")).suffix.lower()
            dest = dst / safe_name(prefix, ix, ext)
            if not dest.exists() and not dest.with_suffix(".webp").exists():
                try:
                    fetch_file(item, dest, PDF_MAX if ext == ".pdf" else IMAGE_MAX)
                except Exception as exc:
                    print("ПРОПУЩЕНО:", item.get("name"), str(exc)[:130])
                    continue
            if ext != ".pdf":
                dest = optimize_image(dest) if dest.exists() else dest.with_suffix(".webp")
            if not dest.exists():
                continue
            cumulative += size
            uri = "/" + dest.relative_to(ROOT / "public").as_posix()
            print("ЗАГРУЖЕНО:", uri)
            if kind == "menu":
                raw = Path(item.get("name", "")).stem.replace("_", " ").replace("-", " ")
                title = raw[:55] if any(c.isalpha() for c in raw) else f"Страница меню {ix}"
                downloaded_menus.append({"title": title, "url": uri, "format": ("pdf" if ext == ".pdf" else "image")})
            else:
                downloaded_photos.append(uri)
    if not downloaded_photos and not downloaded_menus:
        raise RuntimeError("Не удалось скачать подходящие файлы. Существующий сайт оставлен без изменений.")

    gallery = ROOT / "content/gallery.json"
    info = json.loads(gallery.read_text(encoding="utf-8"))
    if downloaded_photos:
        existing = [s for s in info.get("gallery", []) if not s.startswith("/uploads/bravis-extra-")]
        info["gallery"] = (existing[:4] + downloaded_photos[:7])[:9]
        gallery.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if downloaded_menus:
        manifest = ROOT / "content/menu_media.json"
        manifest.write_text(json.dumps({"source": SHARE, "files": downloaded_menus}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        builder = ROOT / "src/build.py"
        if "BRAVIS_ADDITIONAL_MENU_GALLERY_V1" not in builder.read_text(encoding="utf-8"):
            shutil.copy2(builder, builder.with_suffix(".py.before-extra-media"))
            inject_menu_gallery(builder)
        css = ROOT / "public/assets/site.css"
        old = css.read_text(encoding="utf-8")
        if "BRAVIS additional original menu pages" not in old:
            css.write_text(old + "\n" + STYLE, encoding="utf-8")
    print("ИМПОРТ:", len(downloaded_photos), "фотографий;", len(downloaded_menus), "файлов меню")
    print("Следующий шаг: python3 src/build.py && python3 verify.py && bash install-preview.sh /home/a4dev/bravis-site")

def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true")
    group.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        files, ndirs, calls = scan()
    except Exception as e:
        print("Ошибка получения списка Яндекс Диска:", str(e)[:300])
        return 1
    menus = [item for item in files if classify(item) == "menu"]
    photos = [item for item in files if classify(item) == "photo"]
    print("Папка:", SHARE)
    print("Найдено:", len(files), "файлов, папок:", ndirs, "запросов API:", calls)
    print("Подходят:", len(photos), "фотографий,", len(menus), "изображений/PDF меню")
    print("МЕНЮ:"); description(menus)
    print("ФОТО:"); description(photos[:12])
    if not args.apply:
        return 0
    if not menus:
        print("ВНИМАНИЕ: Файлы меню не распознаны по названиям папок и файлов. Цены не выдумываются.")
    try:
        apply(photos, menus)
    except Exception as e:
        print("ИМПОРТ НЕ ВЫПОЛНЕН:", str(e))
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())
