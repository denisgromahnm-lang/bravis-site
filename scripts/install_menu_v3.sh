#!/usr/bin/env bash
# BRAVIS menu v3: keep only unique menu pages, with one thumbnail for each category.
# Preview only. Server hostname guard, no DNS or running-service changes.
set -Eeuo pipefail
EXPECTED_HOST='9394005-on250182'
if [[ "$(hostname -s)" != "$EXPECTED_HOST" ]]; then
  echo 'СТОП: это не российский сервер сайта BRAVIS'; exit 2
fi
ROOT='/home/a4dev/bravis-ready'
SITE='/home/a4dev/bravis-site'
[[ -f "$ROOT/src/build.py" && -f "$ROOT/content/menu_media.json" && -f "$SITE/dist/index.html" ]] || {
  echo 'СТОП: исходники/предпросмотр BRAVIS не обнаружены'; exit 3
}
for cmd in curl python3 pdftoppm pdfinfo base64 gzip sha256sum; do
  command -v "$cmd" >/dev/null || { echo "СТОП: требуется $cmd"; exit 4; }
done
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
SCRIPT_URL='https://raw.githubusercontent.com/denisgromahnm-lang/bravis-site/4fcdaf2dd7369321426acb105c1595510e38a8c0/scripts/fix_menu_duplicates_v3.py.gz.b64'
echo '[1/4] Получаю и проверяю скрипт BRAVIS v3 из GitHub'
curl -fsSL --retry 1 --connect-timeout 10 --max-time 60 "$SCRIPT_URL" -o "$TMP/menu_v3.b64"
base64 -d "$TMP/menu_v3.b64" | gzip -dc > "$TMP/menu_v3.py"
echo "c5e4069cbf8223b66c0ec285f77e4a962a743a204ed0f89d196b4653de297859  $TMP/menu_v3.py" | sha256sum -c -
python3 -m py_compile "$TMP/menu_v3.py"
echo '[2/4] Удаляю дубликаты страниц PDF и создаю пять видимых разделов меню'
python3 "$TMP/menu_v3.py" --apply
cd "$ROOT"
echo '[3/4] Собираю сайт, проверяю меню и отсутствие PDF-ссылок'
python3 src/build.py
python3 verify.py
python3 - <<'PY'
import json
from pathlib import Path
root=Path('/home/a4dev/bravis-ready')
manifest=json.loads((root/'content/menu_media.json').read_text(encoding='utf8'))
assert manifest.get('selection')=='owner-approved-unique-image-v3', 'Menu version mismatch'
files=manifest['files']
expected={'seasonal','main-front','main-back','business','children'}
assert {x.get('group') for x in files}==expected, 'Missing menu category'
assert len(files)==5, 'Expected five unique preview pages, found '+str(len(files))
for obj in files:
  assert obj.get('format')=='image' and obj['url'].endswith(('.jpg','.jpeg','.png','.webp'))
  assert (root/'dist'/obj['url'].lstrip('/')).is_file(),obj['url']
content=(root/'dist/menu/index.html').read_text(encoding='utf8')
for key in expected:
  assert '/menu-media/'+key in content,key
assert 'BRAVIS' in content and 'noindex' in content
assert '.pdf' not in content.lower(), 'Menu still links to PDF'
assert 'Актуальное меню бизнес-ланча уточняйте' not in content, 'Business lunch still hidden'
print('PASS: five visible image menus, no PDF links, no duplicates, preview noindex')
PY
echo '[4/4] Обновляю только защищённый предпросмотр с резервной копией'
bash install-preview.sh "$SITE"
echo 'ГОТОВО: на сайте пять обложек меню; основной PDF и бизнес-ланч без повторяющихся страниц.'
echo 'Исходные PDF сохранены в /home/a4dev/bravis-ready/.menu-backups.'
echo 'DNS, индексирование и службы A4 REST AI не изменены.'
