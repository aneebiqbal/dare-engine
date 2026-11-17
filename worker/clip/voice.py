"""Mix a voice-over bed under the gameplay audio, ducking the game sound.

`cues` is a list of (start_seconds, wav_path). The voice track is delayed to
each cue, mixed, then used as the sidechain for `sidechaincompress` so the
gameplay audio dips only while the voice is speaking.
"""
from __future__ import annotations

import subprocess


def mix_voice_over(video_path: str, cues: list[tuple[float, str]], out_path: str) -> str:
    if not cues:
        raise ValueError("no voice cues")
    cmd = ["ffmpeg", "-y", "-i", video_path]
    labels = []
    for i, (start, wav) in enumerate(cues):
        cmd += ["-i", wav]
        delay = int(max(0.0, start) * 1000)
        labels.append(f"[{i + 1}:a]adelay={delay}|{delay}[v{i}]")
    bed = "".join(f"[v{i}]" for i in range(len(cues)))
    filter_complex = ";".join(
        labels
        + [
            f"{bed}amix=inputs={len(cues)}:normalize=0[voice]",
            "[0:a]asplit=2[game][sc]",
            "[game][voice]sidechaincompress=threshold=0.05:ratio=10:attack=20:release=250[duck]",
            "[duck][voice]amix=inputs=2:duration=first:normalize=0[aout]",
        ]
    )
    cmd += [
        "-filter_complex", filter_complex,
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        out_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"voice mix failed: {proc.stderr[-1500:]}")
    return out_path
