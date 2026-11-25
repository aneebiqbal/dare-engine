#!/usr/bin/env bash
# Prepare a production release: copy the installers into the web app's public
# downloads folder and write the manifest the landing page reads.
#
#   scripts/prepare-release.sh 0.1.0 ./Clipdesk_0.1.0_aarch64.dmg ./Clipdesk_0.1.0_x64.exe [demo.mp4]
#
# Run it before pushing (or on the server after cloning) so /landing offers
# real files. Binaries stay gitignored; only releases/manifest.json is committed.
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "usage: $0 <version> <mac.dmg> <windows.exe> [demo.mp4]" >&2
  exit 2
fi

VERSION="$1"
MAC="$2"
WIN="$3"
DEMO="${4:-}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="$ROOT/web/public/downloads"
mkdir -p "$DIR"

[ -f "$MAC" ] || { echo "not found: $MAC" >&2; exit 1; }
[ -f "$WIN" ] || { echo "not found: $WIN" >&2; exit 1; }

cp -f "$MAC" "$DIR/Clipdesk_${VERSION}_aarch64.dmg"
cp -f "$WIN" "$DIR/Clipdesk_${VERSION}_x64.exe"
[ -n "$DEMO" ] && cp -f "$DEMO" "$DIR/demo.mp4"

A="Clipdesk_${VERSION}_aarch64.dmg"
W="Clipdesk_${VERSION}_x64.exe"
export ROOT

python3 - "$VERSION" "$DIR" "$A" "$W" "$DEMO" <<'PY'
import hashlib, json, os, sys

version, directory, mac_name, win_name, demo = sys.argv[1:6]

def entry(eid, title, body, requirements, name):
    path = os.path.join(directory, name)
    data = open(path, "rb").read()
    return {
        "id": eid, "title": title, "body": body, "requirements": requirements,
        "file": name, "url": "", "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }

downloads = [
    entry("mac", "macOS",
          "The admin's local engine: capture, SSD import, MLX Whisper, models and rendering. Nothing heavy leaves the Mac.",
          "macOS 13+, Apple Silicon", mac_name),
    entry("windows", "Windows",
          "The same shell on Windows, with the bundled FFmpeg recorder. See docs/desktop-app.md for the build and signing steps.",
          "Windows 10+, 64-bit", win_name),
]
demo_file = "demo.mp4" if demo and os.path.exists(os.path.join(directory, "demo.mp4")) else ""
manifest = {
    "version": version,
    "web_portal_url": "",
    "demo_clip": {"file": demo_file, "url": ""},
    "downloads": downloads,
}
with open(os.path.join(os.environ["ROOT"], "web", "releases", "manifest.json"), "w") as fh:
    json.dump(manifest, fh, indent=2)
    fh.write("\n")
print(json.dumps(manifest, indent=2))
PY
