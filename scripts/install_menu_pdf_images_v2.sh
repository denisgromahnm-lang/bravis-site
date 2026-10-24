#!/usr/bin/env bash
# BRAVIS preview only. Converts approved PDFs to JPEG; unreadable business PDF becomes phone notice.
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
  'https://raw.githubusercontent.com/denisgromahnm-lang/bravis-site/6e928bce80bf3d363aa8214c16a11bb4a2176648/scripts/render_menu_pdf_as_images_v2.py' \
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
    assert item["format"] in ("image","notice"), "PDF must not be linked directly"
    if item["format"]=="image":
        assert (p/"dist"/item["url"].lstrip("/")).is_file(), item["url"]
    else:
        assert item["title"]=="Бизнес-ланч" and not item["url"], "Only business fallback allowed"
html=(p/"dist/menu/index.html").read_text(encoding="utf-8")
assert "/menu-media/main-front-page-" in html
if any(item["format"]=="notice" for item in menu["files"]):
    assert "Актуальное меню бизнес-ланча уточняйте" in html
else:
    assert "/menu-media/business-page-" in html
assert "/menu-media/children-page-" in html
assert "noindex" in html
assert "/menu-media/business.pdf" not in html
assert "/menu-media/main-front.pdf" not in html
assert "/menu-media/children.pdf" not in html
print("PASS: PDF browser links removed, image pages/notice verified, noindex preserved")
PY
echo "[4/4] Обновляю только защищённый предпросмотр"
bash install-preview.sh "$TARGET"
echo "ГОТОВО: меню переведено в изображения; если бизнес-PDF пустой, вместо него показан телефон."
echo "Если исходный PDF оказался пустым, скрипт остановится ДО замены сайта."
