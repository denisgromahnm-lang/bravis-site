#!/usr/bin/env bash
# BRAVIS preview only. Converts approved PDF menu pages to JPEG.
set -Eeuo pipefail
if [[ "$(hostname -s)" != "9394005-on250182" ]]; then
  echo "СТОП: эта команда только для российского сервера BRAVIS"; exit 2
fi
ROOT="/home/a4dev/bravis-ready"
TARGET="/home/a4dev/bravis-site"
if [[ ! -f "$ROOT/content/menu_media.json" || ! -f "$ROOT/src/build.py" || ! -f "$TARGET/dist/index.html" ]]; then
  echo "СТОП: нет готового проекта BRAVIS"; exit 3
fi
if ! command -v pdftoppm >/dev/null || ! command -v pdfinfo >/dev/null; then
  echo "Устанавливаю только системную утилиту poppler-utils для PDF (без обновления других пакетов)"
  if [[ "$EUID" -ne 0 ]]; then
    echo "СТОП: для отсутствующего poppler-utils требуются права администратора"; exit 4
  fi
  export DEBIAN_FRONTEND=noninteractive
  if ! apt-get install -y -qq --no-install-recommends poppler-utils; then
    apt-get update -qq
    apt-get install -y -qq --no-install-recommends poppler-utils
  fi
fi
TEMP="$(mktemp -d)"
trap 'rm -rf "$TEMP"' EXIT
echo "[1/4] Получаю проверенный скрипт подготовки изображений"
curl -fsSL --retry 1 --connect-timeout 10 --max-time 60 \
  'https://raw.githubusercontent.com/denisgromahnm-lang/bravis-site/aee89e28d33d2f2b2b6170aaae46a4ccf7ad8097/scripts/render_menu_pdf_as_images.py' \
  -o "$TEMP/render_menu.py"
python3 -m py_compile "$TEMP/render_menu.py"
echo "[2/4] Рендерю PDF, проверяю страницы и сохраняю оригиналы"
python3 "$TEMP/render_menu.py" --apply
echo "[3/4] Проверяю сборку"
cd "$ROOT"
python3 src/build.py
python3 verify.py
python3 - <<'PY'
import json
from pathlib import Path
p=Path("/home/a4dev/bravis-ready")
menu=json.loads((p/"content/menu_media.json").read_text(encoding="utf-8"))
for item in menu["files"]:
    assert item["format"]=="image", "PDF should not be used as website card"
    assert (p/"dist"/item["url"].lstrip("/")).is_file(), item["url"]
html=(p/"dist/menu/index.html").read_text(encoding="utf-8")
assert "/menu-media/main-front-page-" in html
assert "/menu-media/business-page-" in html
assert "/menu-media/children-page-" in html
assert "noindex" in html
print("PASS: menu images linked, generated, noindex preserved")
PY
echo "[4/4] Обновляю только защищённый предпросмотр"
bash install-preview.sh "$TARGET"
echo "ГОТОВО: PDF меню преобразованы в изображения, обнови страницу меню Ctrl+F5."
echo "Если исходный PDF оказался пустым, скрипт остановится ДО замены сайта."
