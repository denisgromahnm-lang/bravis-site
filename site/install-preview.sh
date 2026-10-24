#!/usr/bin/env bash
set -euo pipefail
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-/home/a4dev/bravis-site}"
if [[ "$TARGET" != "/home/a4dev/bravis-site" ]]; then
  echo 'STOP: refusing to modify a different project'; exit 2
fi
if [[ ! -f "$TARGET/dist/index.html" ]]; then
  echo 'STOP: existing preview not found'; exit 3
fi
if [[ ! -f "$SOURCE_DIR/site.config.json" ]]; then
  echo 'STOP: release incomplete'; exit 4
fi
cd "$SOURCE_DIR"
python3 src/build.py
python3 verify.py
# Keep the destination dist DIRECTORY INODE unchanged. Some preview servers have
# their current working directory inside dist, so renaming dist would keep them
# serving the old files even after a successful deployment.
export BRAVIS_SOURCE="$SOURCE_DIR/dist" BRAVIS_TARGET="$TARGET/dist"
python3 - <<'PY'
from pathlib import Path
import os, shutil, datetime
src = Path(os.environ['BRAVIS_SOURCE'])
target = Path(os.environ['BRAVIS_TARGET'])
backup = target.parent / ('dist.backup.' + datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
shutil.copytree(target, backup)
try:
    old_files = {p.relative_to(target) for p in target.rglob('*') if p.is_file()}
    shutil.copytree(src, target, dirs_exist_ok=True)
    new_files = {p.relative_to(src) for p in src.rglob('*') if p.is_file()}
    for rel in old_files - new_files:
        p = target / rel
        if p.is_file(): p.unlink()
    for p in sorted(target.rglob('*'), key=lambda x:len(x.parts), reverse=True):
        if p.is_dir() and not any(p.iterdir()):p.rmdir()
except Exception:
    # Restore without renaming dist, for compatibility with running file servers.
    for p in list(target.iterdir()):
        if p.is_dir():shutil.rmtree(p)
        else:p.unlink()
    shutil.copytree(backup, target, dirs_exist_ok=True)
    raise
print('Installed BRAVIS preview in-place; backup:', backup)
PY
