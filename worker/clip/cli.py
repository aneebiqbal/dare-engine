"""Render one Short from a file and two timestamps.

Usage:
    python -m clip.cli <input> --start 8 --end 40 --card card.json --out-dir ./out
"""
from __future__ import annotations

import argparse
import dataclasses
import json

from .engine import render_short


def main() -> None:
    parser = argparse.ArgumentParser(prog="clip")
    parser.add_argument("input")
    parser.add_argument("--start", type=float, required=True)
    parser.add_argument("--end", type=float, required=True)
    parser.add_argument("--card", required=True)
    parser.add_argument("--result", default="")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--template", default=None)
    args = parser.parse_args()

    with open(args.card) as fh:
        card = json.load(fh)

    from .llm import get_llm

    result = render_short(
        args.input, card, args.start, args.end,
        args.out_dir, args.result, args.template, get_llm(),
    )
    print(json.dumps(dataclasses.asdict(result), indent=2))


if __name__ == "__main__":
    main()
