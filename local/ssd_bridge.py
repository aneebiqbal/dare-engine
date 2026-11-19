"""Host-side SSD bridge for the studio.

The API container cannot see /Volumes, so this small stdlib HTTP server runs on
the Mac: it lists the videos on mounted external drives and copies a chosen file
into a shared inbox (~/.clipdesk/ssd-inbox) that the container bind-mounts.

    make ssd-bridge     # then open the studio and choose "Import from SSD"

Nothing leaves the machine: the copy is local, and the API then imports from the
inbox into its own local storage.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MOUNT = pathlib.Path(os.environ.get("SSD_MOUNT_DIR", "/Volumes"))
INBOX = pathlib.Path(
    os.environ.get("SSD_INBOX_DIR", pathlib.Path.home() / ".clipdesk" / "ssd-inbox")
)
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".m4v", ".avi", ".webm", ".mpg", ".mpeg"}
MAX_FILES = 400
PORT = int(os.environ.get("SSD_BRIDGE_PORT", "8799"))


def probe(path: pathlib.Path) -> dict:
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-show_entries", "stream=codec_type,width,height",
                "-of", "json", str(path),
            ],
            capture_output=True, text=True, timeout=30,
        )
        data = json.loads(out.stdout)
        width = height = 0
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                width, height = stream.get("width", 0), stream.get("height", 0)
                break
        return {
            "duration_seconds": round(float(data["format"]["duration"]), 3),
            "width": width,
            "height": height,
        }
    except Exception as exc:
        return {"error": type(exc).__name__}


def _videos(root: pathlib.Path) -> list[dict]:
    found = []
    # Top level plus one level of folders: fast, and where camera rolls live.
    candidates = []
    try:
        candidates.extend(p for p in root.iterdir() if p.is_file())
        candidates.extend(
            p for child in root.iterdir() if child.is_dir() for p in child.iterdir()
        )
    except Exception:
        pass
    for path in sorted(candidates):
        if len(found) >= MAX_FILES:
            break
        if not path.is_file() or path.suffix.lower() not in VIDEO_EXTS:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        found.append({
            "name": str(path.relative_to(root)),
            "path": str(path),
            "size_bytes": stat.st_size,
            **probe(path),
        })
    return found


def drives() -> list[dict]:
    out = []
    try:
        volumes = sorted(p for p in MOUNT.iterdir() if p.is_dir())
    except Exception as exc:
        return [{"name": str(MOUNT), "error": type(exc).__name__, "videos": []}]
    for volume in volumes:
        if volume.name == "Macintosh HD":
            continue
        out.append({"name": volume.name, "path": str(volume), "videos": _videos(volume)})
    return out


def import_file(path: str) -> dict:
    source = pathlib.Path(path).resolve()
    try:
        source.relative_to(MOUNT.resolve())
    except ValueError:
        raise ValueError("refusing to import a path outside the mount dir")
    if not source.is_file():
        raise ValueError("not a file")
    INBOX.mkdir(parents=True, exist_ok=True)
    target = INBOX / f"{uuid.uuid4().hex}{source.suffix.lower()}"
    shutil.copy2(source, target)
    return {"filename": target.name, "inbox_path": str(target), "size_bytes": target.stat().st_size}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code: int, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/drives":
            self._send(200, {"mount": str(MOUNT), "drives": drives()})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/import":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            self._send(200, import_file(payload["path"]))
        except Exception as exc:
            self._send(400, {"error": f"{type(exc).__name__}: {exc}"})


def main() -> int:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"SSD bridge on http://0.0.0.0:{PORT} (mount {MOUNT}, inbox {INBOX})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
