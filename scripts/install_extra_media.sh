#!/usr/bin/env bash
# BRAVIS: preview-only import from second public Yandex Disk folder.
# Target host is the Russian VPS, never the Netherlands gateway.
set -Eeuo pipefail
if [[ "$(hostname -s)" != "9394005-on250182" ]]; then
  echo "СТОП: это не российский сервер BRAVIS"; exit 2
fi
TARGET="/home/a4dev/bravis-site"
READY="/home/a4dev/bravis-ready"
[[ -f "$TARGET/dist/index.html" ]] || { echo "СТОП: действующий предпросмотр не найден"; exit 3; }
for cmd in curl base64 tar sha256sum python3; do
  command -v "$cmd" >/dev/null || { echo "СТОП: нет программы $cmd"; exit 4; }
done
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Rehydrate a persistent copy of the previous tested release, if missing.
if [[ ! -f "$READY/src/build.py" || ! -f "$READY/install-preview.sh" ]]; then
  echo "[1/5] Восстанавливаю исходники BRAVIS из закреплённого релиза"
  mkdir -p "$READY"
  curl -fsSL --retry 1 --connect-timeout 10 --max-time 80 \
    'https://raw.githubusercontent.com/denisgromahnm-lang/bravis-site/81d627d348c30a2922e875603270cc3fb9f7cba2/release/bravis-site.tar.gz.b64' \
    -o "$TMP/site.b64"
  base64 -d "$TMP/site.b64" > "$TMP/site.tar.gz"
  echo "05b7dae3da0d2d71192f46b933f0628c482e20a4ff4e52121e5190b4f4cf3ce6  $TMP/site.tar.gz" | sha256sum -c -
  tar -xzf "$TMP/site.tar.gz" -C "$READY"
else
  echo "[1/5] Использую имеющиеся исходники BRAVIS"
fi

# Carry across existing restaurant photos; never substitute interior photos for dishes.
echo "[2/5] Сохраняю уже подключённые фотографии"
if [[ -d "$TARGET/dist/uploads" ]]; then
  mkdir -p "$READY/public/uploads"
  cp -an "$TARGET/dist/uploads/." "$READY/public/uploads/"
fi
export BRAVIS_READY="$READY"
python3 - <<'PY'
import json,os
from pathlib import Path
root=Path(os.environ["BRAVIS_READY"])
manifest=root/"content/gallery.json"
assets=sorted((root/"public/uploads").glob("bravis-*"))
paths=["/uploads/"+x.name for x in assets if x.suffix.lower() in (".jpg",".jpeg",".webp",".png")]
if manifest.is_file() and paths:
    data=json.loads(manifest.read_text(encoding="utf-8"))
    if not data.get("hero"):data["hero"]=paths[0]
    if not data.get("interior"):data["interior"]=paths[min(1,len(paths)-1)]
    if not data.get("events"):data["events"]=paths[min(2,len(paths)-1)]
    if not data.get("gallery"):data["gallery"]=paths[:9]
    manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Исходные фото сохранены:",len(paths))
PY

echo "[3/5] Получаю загрузчик дополнительной папки"
curl -fsSL --retry 1 --connect-timeout 10 --max-time 60 \
  'https://raw.githubusercontent.com/denisgromahnm-lang/bravis-site/4906ff19af6131df6d89773fda4d06683a381749/scripts/import_additional_media.py' \
  -o "$TMP/import_extra.py"
python3 -m py_compile "$TMP/import_extra.py"

echo "[4/5] Проверяю папку и импортирую фото/меню"
python3 "$TMP/import_extra.py" --apply

echo "[5/5] Устанавливаю обновлённый ПРЕДПРОСМОТР с резервной копией"
cd "$READY"
python3 src/build.py
python3 verify.py
bash install-preview.sh "$TARGET"
echo "ГОТОВО: дополнительно загруженные материалы BRAVIS включены в предпросмотр."
echo "Открой прежнюю защищённую ссылку Cloudflare и нажми Ctrl+F5."
echo "Индексация остаётся отключённой. DNS и действующие службы не менялись."
