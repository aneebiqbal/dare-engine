"""Clip engine: a mission window in, a finished 9:16 Short out.

The clip is built from a grammar of beats (cold open, hook, context, payoff,
button), not a concatenation of fixed blocks. See `grammar.py` and
`templates.json`.
"""
from __future__ import annotations

import dataclasses
import json
import subprocess
import tempfile
from pathlib import Path

from .beats import select_setup
from .caption import write_ass, write_srt
from .grammar import Beat, Template, build_beats, get_template, load_templates, pick_template
from .layout import filtergraph
from .policy import detect_letterbox, guard_window, title_flags
from .transcribe import Word, transcribe

WINDOW_BEFORE = 10.0
WINDOW_AFTER = 5.0
PAYOFF_SECONDS = 18.0

NORMALIZE_VF = (
    "scale=1920:1080:force_original_aspect_ratio=increase,"
    "crop=1920:1080,setsar=1,fps=30"
)

_ENCODERS = ("h264_videotoolbox", "h264_nvenc", "h264_qsv", "h264_vaapi", "libx264")
_encoder: str | None = None


def detect_encoder() -> str:
    """Pick a hardware H.264 encoder when there is one, else libx264."""
    global _encoder
    if _encoder is None:
        out = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True
        ).stderr
        _encoder = next((e for e in _ENCODERS if e in out), "libx264")
        print(f"h264 encoder: {_encoder}")
    return _encoder


def codec_args(encoder: str | None = None) -> list[str]:
    enc = encoder or detect_encoder()
    if enc == "libx264":
        return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"]
    if enc == "h264_videotoolbox":
        return ["-c:v", "h264_videotoolbox", "-b:v", "8000k"]
    if enc in ("h264_nvenc", "h264_qsv"):
        return ["-c:v", enc, "-preset", "p4", "-b:v", "8000k"]
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"]


@dataclasses.dataclass
class Result:
    out_path: str
    thumb_path: str
    srt_path: str
    metadata_path: str
    duration: float
    layout: str
    flags: dict
    template: str = ""
    beats: list[Beat] | None = None
    words_abs: list["Word"] | None = None


def _run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed: {' '.join(cmd)}\n{proc.stderr[-2000:]}"
        )
    return proc.stdout


def _duration(path: str) -> float:
    out = _run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1", path,
        ]
    ).strip()
    return float(out)


def _has_audio(path: str) -> bool:
    out = _run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=index",
            "-of", "csv=p=0", path,
        ]
    ).strip()
    return bool(out)


def _dimensions(path: str) -> tuple[int, int]:
    out = _run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0:s=x", path,
        ]
    ).strip()
    width, height = out.split("x")
    return int(width), int(height)


def _is_landscape(path: str) -> bool:
    width, height = _dimensions(path)
    return width >= height


def _cut(src: str, out: str, start: float, length: float) -> None:
    cmd = ["ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", src]
    maps = ["-map", "0:v:0"]
    if _has_audio(src):
        maps += ["-map", "0:a:0"]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        maps += ["-map", "1:a:0"]
    cmd += [
        "-t", f"{length:.3f}",
        "-vf", NORMALIZE_VF,
        "-pix_fmt", "yuv420p",
        *codec_args(),
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
        *maps, out,
    ]
    _run(cmd)


def _strongest_second(words: list[Word], lo: float, hi: float) -> float:
    scores: dict[int, int] = {}
    for w in words:
        mid = (w.start + w.end) / 2
        if lo <= mid < hi:
            scores[int(mid)] = scores.get(int(mid), 0) + 1
    if not scores:
        return (lo + hi) / 2
    return float(max(scores.items(), key=lambda kv: (kv[1], -kv[0]))[0])


def _resolve_template(
    template: str | None, template_id: str | None, seed: str
) -> Template:
    caption_styles, templates = load_templates()
    if template_id:
        return get_template(template_id)
    if template and any(t.id == template for t in templates):
        return get_template(template)
    chosen = pick_template(seed)
    if template and any(t.layout == template for t in templates):
        # A layout name from a re-render overrides the rotated template's layout.
        return dataclasses.replace(chosen, layout=template)
    return chosen


def render_short(
    input_path: str,
    card: dict,
    start: float,
    end: float,
    out_dir: str,
    result_value: str = "",
    template: str | None = None,
    llm=None,
    words_abs: list["Word"] | None = None,
    caption_style: str = "word",
    template_id: str | None = None,
) -> Result:
    src = str(input_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    file_duration = _duration(src)
    win_start = max(0.0, start - WINDOW_BEFORE)
    win_end = min(file_duration, end + WINDOW_AFTER)
    if win_end - win_start < 5:
        raise ValueError(f"window {win_start:.1f}-{win_end:.1f}s is too short")

    payoff_end = min(win_end, end)
    payoff_start = max(win_start, payoff_end - PAYOFF_SECONDS)

    with tempfile.TemporaryDirectory(prefix="clipdesk-") as tmp:
        tmp = Path(tmp)

        window = tmp / "window.mp4"
        _cut(src, str(window), win_start, win_end - win_start)
        if words_abs is None:
            words = transcribe(str(window))
            words_abs = [Word(w.start + win_start, w.end + win_start, w.text) for w in words]
        else:
            # Cached transcript is in source-recording time; re-window it.
            words = [
                Word(w.start - win_start, w.end - win_start, w.text)
                for w in words_abs
                if win_start <= (w.start + w.end) / 2 < win_end
            ]

        guard_window(words, payoff_start - win_start, payoff_end - win_start)
        letterbox = detect_letterbox(str(window), *_dimensions(str(window)))

        rel_payoff_lo = payoff_start - win_start
        rel_payoff_hi = payoff_end - win_start
        peak = win_start + _strongest_second(words, rel_payoff_lo, rel_payoff_hi)

        seed = f"{card.get('id', '')}:{start:.0f}:{end:.0f}"
        tpl = _resolve_template(template, template_id, seed)
        layout = tpl.layout
        captions = caption_style or tpl.captions

        setup = select_setup(words, 0.0, max(0.0, rel_payoff_lo), llm)
        context_range = None
        if setup:
            s, e = setup[0]
            context_range = (win_start + s, win_start + e)

        beats = build_beats(tpl, peak, payoff_start, payoff_end, context_range)
        for beat in beats:
            beat.src_start = max(0.0, min(beat.src_start, file_duration - 0.2))
            beat.length = max(0.4, min(beat.length, file_duration - beat.src_start))

        parts: list[Path] = []
        for i, beat in enumerate(beats):
            clip = tmp / f"beat{i}.mp4"
            _cut(src, str(clip), beat.src_start, beat.length)
            parts.append(clip)

        concat = tmp / "concat.txt"
        concat.write_text("".join(f"file '{p}'\n" for p in parts))
        timeline = tmp / "timeline.mp4"
        _run(
            [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
                str(timeline),
            ]
        )

        # Map window-relative word times onto the output timeline. Beat source
        # ranges are disjoint, so captions stay word-synced and in order.
        events: list[tuple[float, float, float, float]] = []
        t = 0.0
        for beat in beats:
            events.append((beat.src_start, beat.src_start + beat.length, t, t + beat.length))
            t += beat.length
        total = t

        mapped: list[Word] = []
        for w in words:
            st = win_start + w.start
            en = win_start + w.end
            for slo, shi, olo, ohi in events:
                if slo <= st < shi:
                    offset = (st - slo) / (shi - slo) * (ohi - olo)
                    mapped.append(Word(olo + offset, olo + offset + (en - st), w.text))
                    break
        mapped.sort(key=lambda w: w.start)

        mission_num = str(card.get("id", "")).replace("m_", "")
        end_lines = [f"MISSION {mission_num}" if mission_num else "MISSION"]
        if result_value:
            end_lines.append(str(result_value))
        end_start = max(0.0, total - tpl.button_seconds)

        ass_path = tmp / "burn.ass"
        hook_dur = min(tpl.hook_seconds, beats[-1].length) if beats else 2.0
        write_ass(
            str(ass_path), card.get("hook_text", ""), hook_dur,
            mapped if captions != "none" else [], end_lines, end_start, total,
            caption_style=captions,
        )
        srt_path = out_dir / "captions.srt"
        write_srt(str(srt_path), mapped, caption_style=captions)

        out_path = out_dir / "short.mp4"
        vf = f"{filtergraph(layout)};[v]subtitles=filename={ass_path}[outv]"
        _run(
            [
                "ffmpeg", "-y", "-i", str(timeline),
                "-filter_complex", vf, "-map", "[outv]", "-map", "0:a:0?",
                "-pix_fmt", "yuv420p", "-r", "30",
                *codec_args(),
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart", str(out_path),
            ]
        )

        thumb = out_dir / "thumb.jpg"
        _run(
            [
                "ffmpeg", "-y", "-ss", f"{total / 2:.3f}", "-i", str(out_path),
                "-frames:v", "1", "-q:v", "3", str(thumb),
            ]
        )

        duration = _duration(str(out_path))
        flags = title_flags(card.get("title_options", [""])[0])
        metadata = {
            "mission_id": card.get("id"),
            "question": card.get("question"),
            "title": card.get("title_options", [""])[0],
            "description": f"{card.get('question', '')}\n\nMission {mission_num}.",
            "tags": ["clipdesk", "missions", card.get("mode", "")],
            "layout": layout,
            "template": tpl.id,
            "caption_style": captions,
            "beats": [{"kind": b.kind, "src_start": round(b.src_start, 2),
                       "length": round(b.length, 2)} for b in beats],
            "duration_seconds": round(duration, 3),
            "result": result_value,
            "encoder": detect_encoder(),
            "title_flags": flags,
            "spoiler_flags": letterbox,
        }
        metadata_path = out_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2))

        return Result(
            out_path=str(out_path),
            thumb_path=str(thumb),
            srt_path=str(srt_path),
            metadata_path=str(metadata_path),
            duration=duration,
            layout=layout,
            flags=letterbox,
            template=tpl.id,
            beats=beats,
            words_abs=words_abs,
        )
