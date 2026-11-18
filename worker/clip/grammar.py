"""The clip grammar: a template of beats, not a concatenation of blocks.

Templates live in `templates.json` so new ones are added without code. Each clip
opens on the moment (cold open), carries the hook text, an optional tight context
beat, the payoff, and a clean button at the end.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib

TEMPLATES_PATH = pathlib.Path(__file__).resolve().parent / "templates.json"


@dataclasses.dataclass
class Beat:
    src_start: float
    length: float
    kind: str  # hook | context | payoff


@dataclasses.dataclass
class Template:
    id: str
    hook_seconds: float
    cold_open: float
    context_seconds: float
    button_seconds: float
    layout: str
    captions: str


def load_templates() -> tuple[dict, list[Template]]:
    data = json.loads(TEMPLATES_PATH.read_text())
    templates = [Template(**t) for t in data["templates"]]
    return data["caption_styles"], templates


def get_template(template_id: str) -> Template:
    _, templates = load_templates()
    for t in templates:
        if t.id == template_id:
            return t
    raise ValueError(f"unknown template {template_id!r}")


def pick_template(seed: str, previous_id: str | None = None) -> Template:
    """Rotate templates by a stable hash, never repeating the previous one."""
    _, templates = load_templates()
    digest = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    order = [t for t in templates if t.id != previous_id] or templates
    return order[digest % len(order)]


def build_beats(
    template: Template,
    peak: float,
    payoff_start: float,
    payoff_end: float,
    context_range: tuple[float, float] | None,
) -> list[Beat]:
    """Beats in output order. The cold open is the payoff's peak, on screen
    first; an optional tight context beat is a flash-back after it; the payoff
    itself is the longest beat and ends the clip."""
    cold = max(0.0, min(template.cold_open, template.hook_seconds))
    payoff_src = max(payoff_start, min(peak - cold / 2.0, payoff_end - 1.0))
    cold_len = max(0.0, min(cold, payoff_end - payoff_src))
    beats: list[Beat] = []
    if cold_len > 0.2:
        beats.append(Beat(payoff_src, cold_len, "cold_open"))
    cursor = payoff_src + cold_len
    if template.context_seconds > 0 and context_range:
        ctx_lo, ctx_hi = context_range
        ctx_hi = min(ctx_hi, payoff_src)
        if ctx_hi - ctx_lo >= 1.0:
            length = min(template.context_seconds, ctx_hi - ctx_lo)
            beats.append(Beat(ctx_hi - length, length, "context"))
    if payoff_end - cursor > 0.5:
        beats.append(Beat(cursor, payoff_end - cursor, "payoff"))
    return beats
