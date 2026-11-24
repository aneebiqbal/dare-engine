"""faster-whisper word timestamps over the mission window only."""
from __future__ import annotations

import dataclasses
import gc
import threading

_lock = threading.Lock()
_model = None
# The path that actually ran last, so a bridge fallback is never reported as a
# GPU path. `whisper_compute()` is the configured path; `actual_compute()` is
# what ran.
_last_compute: tuple[str, str] | None = None
# Detected spoken language of the most recent transcription (Whisper's code).
_last_language: str | None = None


def last_language() -> str | None:
    return _last_language


@dataclasses.dataclass(frozen=True)
class Word:
    start: float
    end: float
    text: str


def _cpu_compute(settings) -> tuple[str, str]:
    device, compute = settings.whisper_device, settings.whisper_compute_type
    if device == "cpu" and compute == "int8":
        try:
            import ctranslate2

            if ctranslate2.get_cuda_device_count() > 0:
                return "cuda", "float16"
        except Exception:
            pass
    return device, compute


def whisper_compute() -> tuple[str, str]:
    """The configured path: host MLX Whisper, CUDA, or CPU int8.

    An explicit non-default WHISPER_DEVICE/WHISPER_COMPUTE_TYPE wins, so an
    operator can pin the path; the default pair means "detect".
    """
    from worker_app.config import settings
    from worker_app.settings_store import get as stored

    asr = (stored("asr") or "").lower()
    if asr == "cpu":
        return _cpu_compute(settings)
    if asr == "mlx" and not settings.mlx_whisper_url:
        return _cpu_compute(settings)
    if settings.mlx_whisper_url:
        return "mlx", "metal"
    return _cpu_compute(settings)


def actual_compute() -> tuple[str, str] | None:
    """The path that actually ran, or None before the first transcription."""
    return _last_compute


def _mlx_bridge_words(path: str, language: str | None = None) -> tuple[list[Word], str | None]:
    """Stream the file to the host MLX bridge (the container's storage is not
    visible on the host, so a path would not resolve there). Returns words and
    the detected language."""
    import http.client
    import json
    import pathlib
    import urllib.parse

    from worker_app.config import settings

    parsed = urllib.parse.urlparse(settings.mlx_whisper_url)
    target = pathlib.Path(path)
    # A cut is seconds long; 180 s bounds a pathological input (a music-only or
    # synthetic tone can make Whisper decode forever) so the caller falls back
    # to CPU instead of hanging the stage.
    conn = http.client.HTTPConnection(parsed.hostname, parsed.port or 80, timeout=180)
    conn.putrequest("POST", parsed.path.rstrip("/") + "/transcribe")
    conn.putheader("Content-Type", "application/octet-stream")
    conn.putheader("X-Filename", target.name)
    if language:
        conn.putheader("X-Language", language)
    conn.putheader("Content-Length", str(target.stat().st_size))
    conn.endheaders()
    with open(target, "rb") as handle:
        while chunk := handle.read(1024 * 1024):
            conn.send(chunk)
    resp = conn.getresponse()
    body = resp.read()
    conn.close()
    if resp.status != 200:
        raise RuntimeError(f"MLX bridge returned {resp.status}: {body[:200]!r}")
    data = json.loads(body)
    words = [Word(float(w["start"]), float(w["end"]), w["text"]) for w in data["words"]]
    return words, data.get("language")


def _load(device: str | None = None, compute: str | None = None):
    """Load faster-whisper once. Explicit device/compute are used for the CPU
    fallback, so a configured-but-unreachable MLX bridge can never make
    faster-whisper try to open `device='mlx'`."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        from worker_app.config import settings

        dev, comp = (device, compute) if device else whisper_compute()
        _model = WhisperModel(settings.whisper_model, device=dev, compute_type=comp)
    return _model


def unload() -> None:
    """Drop the resident model so the next pipeline stage starts clean.

    Memory discipline: one model resident at a time, freed and verified before
    the next stage loads its own.
    """
    global _model
    with _lock:
        _model = None
        gc.collect()


def transcribe(path: str, language: str | None = None) -> list[Word]:
    """Word-level timestamps, in seconds from the start of `path`.

    Uses the host MLX Whisper bridge when `MLX_WHISPER_URL` is set (Metal on the
    Mac); otherwise faster-whisper in the container. `language` pins the spoken
    language so a long region cannot drift into a wrong-script hallucination.
    """
    from worker_app.config import settings

    global _last_compute, _last_language
    if settings.mlx_whisper_url:
        try:
            words, detected = _mlx_bridge_words(path, language)
            _last_compute = ("mlx", "metal")
            _last_language = language or detected or _last_language
            return words
        except Exception:
            pass  # bridge configured but unreachable: fall back cleanly to CPU
    _last_compute = _cpu_compute(settings)
    with _lock:
        segments, _info = _load(*_last_compute).transcribe(
            path, word_timestamps=True, vad_filter=False, beam_size=1,
            language=language or None,
        )
    _last_language = language or getattr(_info, "language", None) or _last_language
    words: list[Word] = []
    for seg in segments:
        for w in seg.words or []:
            text = w.word.strip()
            if text:
                words.append(Word(float(w.start), float(w.end), text))
    return words
