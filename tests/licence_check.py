"""Licence check: the default build must contain no GPL/AGPL code.

Voice-over (piper-tts) is an optional, clearly separated add-on and must not
appear in the core requirements.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Direct dependencies and their licences, read from the installed package
# metadata (see docs/context/13-dependencies-and-licences.md).
PYTHON_LICENCES = {
    "fastapi": "MIT",
    "uvicorn": "BSD-3-Clause",
    "psycopg": "LGPL-3.0",
    "pydantic-settings": "MIT",
    "jsonschema": "MIT",
    "boto3": "Apache-2.0",
    "python-multipart": "Apache-2.0",
    "argon2-cffi": "MIT",
    "pyyaml": "MIT",
    "faster-whisper": "MIT",
    "av": "BSD-3-Clause",
    "onnxruntime": "MIT",
    "piper-tts": "GPL-3.0-or-later",
}

NODE_LICENCES = {
    "next": "MIT",
    "react": "MIT",
    "react-dom": "MIT",
    "geist": "SIL OPEN FONT LICENSE",
    "typescript": "Apache-2.0",
    "@types/node": "MIT",
    "@types/react": "MIT",
    "@types/react-dom": "MIT",
    "tailwindcss": "MIT",
    "autoprefixer": "MIT",
    "postcss": "MIT",
}

DENY = ("GPL-1.0", "GPL-2.0", "GPL-3.0", "AGPL")
WEAK_COPYLEFT = ("LGPL", "MPL")


def _core_requirements() -> list[pathlib.Path]:
    return [ROOT / "api" / "requirements.txt", ROOT / "worker" / "requirements.txt"]


def check_licences() -> tuple[bool, list[str]]:
    lines: list[str] = []
    ok = True

    for path in _core_requirements():
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            name = re.split(r"[=<>\[; ]", line, maxsplit=1)[0].strip().lower()
            licence = PYTHON_LICENCES.get(name, "UNKNOWN")
            if licence == "UNKNOWN":
                lines.append(f"WARN  {path.name}: {name} licence unknown")
                continue
            if licence.startswith(DENY):
                ok = False
                lines.append(f"FAIL  {path.name}: {name} is {licence}")
            elif any(licence.startswith(w) for w in WEAK_COPYLEFT):
                lines.append(f"WARN  {path.name}: {name} is {licence} (weak copyleft)")
            else:
                lines.append(f"OK    {path.name}: {name} is {licence}")

    # The GPL voice engine must live only in the optional add-on file.
    optional = ROOT / "worker" / "requirements-voice.txt"
    for path in _core_requirements():
        if "piper-tts" in path.read_text():
            ok = False
            lines.append(f"FAIL  {path.name}: piper-tts (GPL) must not be a core dependency")
    if not optional.exists():
        ok = False
        lines.append("FAIL  worker/requirements-voice.txt is missing")

    package_json = ROOT / "web" / "package.json"
    pkg = json.loads(package_json.read_text())
    for section in ("dependencies", "devDependencies"):
        for name in pkg.get(section, {}):
            licence = NODE_LICENCES.get(name, "UNKNOWN")
            if licence == "UNKNOWN":
                lines.append(f"WARN  package.json: {name} licence unknown")
            elif licence.startswith(DENY):
                ok = False
                lines.append(f"FAIL  package.json: {name} is {licence}")
            else:
                lines.append(f"OK    package.json: {name} is {licence}")

    return ok, lines


def main() -> int:
    ok, lines = check_licences()
    for line in lines:
        print(line)
    print("\nPASS: no GPL/AGPL in the default build" if ok else "\nFAIL: GPL/AGPL in the default build")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
