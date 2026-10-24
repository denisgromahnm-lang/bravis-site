#!/usr/bin/env bash
# BRAVIS only: restrict menu to owner-approved files. Does not touch other services.
set -Eeuo pipefail
if [[ "$(hostname -s)" != "9394005-on250182" ]]; then
 echo "СТОП: запущено не на российском сервере BRAVIS"; exit 2
fi
ROOT="/home/a4dev/bravis-ready"
TARGET="/home/a4dev/bravis-site"
[[ -f "$ROOT/src/build.py" && -f "$ROOT/content/menu_media.json" && -f "$TARGET/dist/index.html" ]] || {
 echo "СТОП: действующий проект не найден"; exit 2;
}
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
echo "[1/4] Загружаю зафиксированный инструмент отбора меню"
curl --fail --silent --show-error --location --connect-timeout 10 --max-time 60 \
  'https://raw.githubusercontent.com/denisgromahnm-lang/bravis-site/4906ff19af6131df6d89773fda4d06683a381749/scripts/import_additional_media.py' \
  -o "$TMP/import_additional_media.py"
curl --fail --silent --show-error --location --connect-timeout 10 --max-time 60 \
  'https://raw.githubusercontent.com/denisgromahnm-lang/bravis-site/54e87374e59ec2b9bb8ba0813ac73f8fe61a5cd2/scripts/select_approved_menu.py' \
  -o "$TMP/select_approved_menu.py"
python3 -m py_compile "$TMP/import_additional_media.py" "$TMP/select_approved_menu.py"
echo "[2/4] Проверяю пять разрешённых файлов и скачиваю их"
python3 "$TMP/select_approved_menu.py" --apply
echo "[3/4] Собираю сайт и проверяю ровно пять меню"
cd "$ROOT"
python3 src/build.py
python3 verify.py
python3 - <<'PY'
import json
from pathlib import Path
root=Path("/home/a4dev/bravis-ready")
items=json.loads((root/"content/menu_media.json").read_text(encoding="utf-8"))["files"]
expected=["seasonal","main-front","main-back","business","children"]
assert len(items)==5, "Menu file count must be 5"
for item,key in zip(items,expected):
    url=item.get("url","")
    assert url.startswith("/menu-media/"+key+"."), "Wrong menu file: "+url
    path=root/"dist"/url.lstrip("/")
    assert path.is_file(), "Menu file missing: "+url
    if key=="children":assert path.suffix.lower()==".pdf", "Children's menu must be PDF"
    if key in ("main-front","business"):assert path.suffix.lower()==".pdf", "Print menu must be PDF"
    assert path.suffix.lower()!=".ai", "AI file forbidden"
menu=(root/"dist/menu/index.html").read_text(encoding="utf-8")
for key in expected: assert "/menu-media/"+key+"." in menu, "Menu link missing: "+key
assert "noindex" in menu
print("PASS: five approved menu files, children's PDF, preview noindex")
PY
echo "[4/4] Обновляю предпросмотр и создаю резервную копию"
bash install-preview.sh "$TARGET"
echo "ГОТОВО: на странице меню только пять согласованных версий. Другие меню скрыты."
echo "Использованы только оригиналы; новые фото не назначались изображениям блюд."
