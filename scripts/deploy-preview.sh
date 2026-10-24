#!/usr/bin/env bash
# BRAVIS preview installer. Updates only /home/a4dev/bravis-site/dist.
# It does not modify DNS, system services, Cloudflare tunnel, or A4 REST.
set -Eeuo pipefail

if [[ "${EUID}" -eq 0 ]]; then
  if command -v runuser >/dev/null && id a4dev >/dev/null 2>&1; then
    echo "Running as a4dev instead of root"
    exec runuser -u a4dev -- bash "$0" "$@"
  fi
  echo "ERROR: Do not run deployment as root. Log in as a4dev." >&2
  exit 2
fi

[[ "$(id -un)" == "a4dev" ]] || { echo "ERROR: expected user a4dev" >&2; exit 2; }
TARGET="/home/a4dev/bravis-site"
[[ -f "$TARGET/dist/index.html" ]] || { echo "ERROR: missing existing BRAVIS preview $TARGET/dist" >&2; exit 2; }
for cmd in curl python3 base64 tar sha256sum; do
  command -v "$cmd" >/dev/null || { echo "ERROR: missing $cmd" >&2; exit 2; }
done

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
URL="https://raw.githubusercontent.com/denisgromahnm-lang/bravis-site/81d627d348c30a2922e875603270cc3fb9f7cba2/release/bravis-site.tar.gz.b64"
EXPECTED_SHA="05b7dae3da0d2d71192f46b933f0628c482e20a4ff4e52121e5190b4f4cf3ce6"
echo "[1/5] Downloading pinned BRAVIS preview release"
curl --fail --show-error --silent --location --connect-timeout 10 --max-time 60 "$URL" -o "$WORK/release.b64"
base64 --decode "$WORK/release.b64" > "$WORK/release.tar.gz"
echo "$EXPECTED_SHA  $WORK/release.tar.gz" | sha256sum -c -

mkdir "$WORK/site"
tar -xzf "$WORK/release.tar.gz" -C "$WORK/site"
cd "$WORK/site"

echo "[2/5] Fetching restaurant photos from public Yandex Disk"
if python3 src/import_yandex.py --download --max 12; then
  echo "Photo import: success"
else
  echo "WARNING: Yandex photos unavailable; existing fallback illustrations remain. No production publishing."
fi
echo "[3/5] Building static HTML and assets"
python3 src/build.py

echo "[4/5] Checking all five pages and local CSS/JS/photo paths"
python3 verify.py

echo "[5/5] Installing to existing preview, preserving dist directory and a backup"
bash install-preview.sh "$TARGET"

echo
echo "PREVIEW UPDATED. Refresh browser with Ctrl+F5."
echo "Indexing remains disabled; domain and existing services were not modified."
echo "The preview tunnel must already be running."
