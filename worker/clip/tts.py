"""Local text-to-speech with Piper (MIT, rhasspy/piper).

The voice model is downloaded separately (`make voice`) because it is a large
binary artefact, not code. The repo-level piper-voices licence is MIT; check the
individual voice card before commercial use.
"""
from __future__ import annotations

import os
import shutil
import subprocess


def voice_path(voice: str, model_dir: str) -> str:
    return os.path.join(model_dir, f"{voice}.onnx")


def list_voices(model_dir: str) -> list[str]:
    if not os.path.isdir(model_dir):
        return []
    return sorted(
        name[: -len(".onnx")]
        for name in os.listdir(model_dir)
        if name.endswith(".onnx")
    )


def speak(
    text: str,
    voice: str,
    out_path: str,
    model_dir: str,
    command: str = "piper",
) -> str:
    model = voice_path(voice, model_dir)
    if not os.path.exists(model):
        raise RuntimeError(f"voice model not found: {model}")
    exe = shutil.which(command)
    if not exe:
        raise RuntimeError(f"TTS command not found: {command}")
    proc = subprocess.run(
        [exe, "--model", model, "--output_file", out_path],
        input=text.encode(),
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"TTS failed: {proc.stderr[-800:].decode(errors='replace')}")
    return out_path
