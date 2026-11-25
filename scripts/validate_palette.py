#!/usr/bin/env python3
"""Print WCAG contrast ratios for the Editorial Graphite + Burnt Coral tokens.

    .venv/bin/python scripts/validate_palette.py

The committed values live in web/app/globals.css and docs/design-direction.md;
if either changes, this script is the check that the pair still passes.
"""
from __future__ import annotations

DARK = {
    "bg": "#171717", "surface": "#1E1E1C", "surface-2": "#292825",
    "border": "#36332F", "text": "#F2F0EB", "muted": "#A49F99",
    "accent": "#E98D72", "accent-ink": "#221512", "accent-soft": "#2A211D",
    "needs": "#D9A441", "success": "#8FB09C", "danger": "#D3776A",
}
LIGHT = {
    "bg": "#F6F2EA", "surface": "#FDFAF3", "surface-2": "#EFE8DC",
    "border": "#DCD2C2", "text": "#221F1C", "muted": "#6E675F",
    "accent": "#AD4B35", "accent-ink": "#FFF6EF", "accent-soft": "#F7EBE2",
    "needs": "#8A5A1F", "success": "#3F6B4F", "danger": "#A83A2C",
}


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
    channel = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def ratio(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


PAIRS = [
    ("text on bg", "text", "bg", 4.5),
    ("text on surface", "text", "surface", 4.5),
    ("muted on surface", "muted", "surface", 4.5),
    ("muted on surface-2", "muted", "surface-2", 4.5),
    ("accent on surface", "accent", "surface", 4.5),
    ("accent on accent-soft", "accent", "accent-soft", 4.5),
    ("accent-ink on accent", "accent-ink", "accent", 4.5),
    ("success on surface", "success", "surface", 4.5),
    ("needs on surface", "needs", "surface", 4.5),
    ("danger on surface", "danger", "surface", 4.5),
]


def main() -> None:
    failed = False
    for name, tokens in (("dark", DARK), ("light", LIGHT)):
        print(f"== {name}")
        for label, fg, bg, minimum in PAIRS:
            value = ratio(tokens[fg], tokens[bg])
            ok = value >= minimum
            failed |= not ok
            print(f"  {'PASS' if ok else 'FAIL'} {label:24s} {value:.2f}:1 (min {minimum})")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
