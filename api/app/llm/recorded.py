"""Replays recorded responses keyed by call kind, so CI needs no key.

The file maps `kind` to a response object. A top-level `cards` key is the
mission-writer response; unknown kinds fall back to the first entry.
"""
import json

from .base import LLM


class RecordedLLM(LLM):
    provider = "recorded"

    def __init__(self, path: str):
        with open(path) as fh:
            data = json.load(fh)
        if isinstance(data, list):
            data = {"_": data}
        if isinstance(data, dict) and set(data) == {"cards"}:
            data = {"cards": data["cards"]}
        self._by_kind = data
        self.model = "recorded"
        self.last_usage = {
            "provider": self.provider,
            "model": self.model,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": 0,
        }

    def complete_json(self, system: str, user: str, schema: dict | None = None, kind: str | None = None) -> dict:
        key = kind or "_"
        if key in self._by_kind:
            return self._by_kind[key]
        return next(iter(self._by_kind.values()))
