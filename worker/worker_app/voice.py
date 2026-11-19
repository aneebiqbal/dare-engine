"""Download a Piper voice model into the shared voices volume.

Usage: python -m worker_app.voice en_US-amy-medium
"""
from __future__ import annotations

import os
import pathlib
import urllib.request

BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
# en/en_US/amy/medium/en_US-amy-medium.onnx
VOICE_PATHS = {
    "en_US-amy-medium": "en/en_US/amy/medium",
}


def download(voice: str, model_dir: str) -> list[str]:
    rel = VOICE_PATHS.get(voice, f"en/en_US/{voice.split('-')[0]}/medium")
    dest = pathlib.Path(model_dir)
    dest.mkdir(parents=True, exist_ok=True)
    written = []
    for name in (f"{voice}.onnx", f"{voice}.onnx.json"):
        target = dest / name
        if target.exists() and target.stat().st_size > 0:
            written.append(str(target))
            continue
        url = f"{BASE}/{rel}/{name}"
        print(f"downloading {url}")
        urllib.request.urlretrieve(url, target)
        written.append(str(target))
    return written


def main() -> None:
    import sys

    from .config import settings

    voice = sys.argv[1] if len(sys.argv) > 1 else settings.tts_voice
    for path in download(voice, settings.tts_model_dir):
        print(path)


if __name__ == "__main__":
    main()
