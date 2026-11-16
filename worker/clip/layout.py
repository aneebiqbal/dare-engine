"""Rotating 9:16 layouts.

No two consecutive Shorts should share a template, so the layout is picked from
a stable hash of the seed (mission id + window) and can be overridden.
"""
from __future__ import annotations

import hashlib

LAYOUTS = ("blur_fit", "center_crop", "fit_height")


def pick_layout(seed: str, landscape: bool = True) -> str:
    """Rotate layouts, but never letterbox a landscape source.

    A 16:9 gameplay capture looks wrong padded into 9:16, so landscape sources
    rotate between the blurred-background and centre-crop layouts.
    """
    options = ("blur_fit", "center_crop") if landscape else ("fit_height", "center_crop")
    digest = hashlib.sha256(seed.encode()).hexdigest()
    return options[int(digest, 16) % len(options)]


def filtergraph(layout: str) -> str:
    """Video part of the filtergraph, ending in the [v] label."""
    if layout == "blur_fit":
        return (
            "split=2[bg][fg];"
            "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,boxblur=20:5[bg2];"
            "[fg]scale=1080:-2,setsar=1[fg2];"
            "[bg2][fg2]overlay=(W-w)/2:(H-h)/2[v]"
        )
    if layout == "center_crop":
        return (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,setsar=1[v]"
        )
    if layout == "fit_height":
        return (
            "scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1[v]"
        )
    raise ValueError(f"unknown layout {layout!r}")
