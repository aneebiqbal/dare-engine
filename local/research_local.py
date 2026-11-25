"""Run the research brain against a local Ollama model. No cloud, no key.

This is the local-engine proof for the M3 Max: the same prompt, schema and
citation filter as `api/app/research.py`, but the one AI client points at
Ollama's OpenAI-compatible endpoint instead of a hosted provider. Chinese
open-weight models (Qwen / Kimi / DeepSeek) run here on Metal.

Run with the project venv (it has jsonschema + fastapi):

    .venv/bin/python local/research_local.py
    LOCAL_MODEL=qwen2.5:7b .venv/bin/python local/research_local.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

_spec = importlib.util.spec_from_file_location("llm_shared", ROOT / "shared" / "llm.py")
llm_shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(llm_shared)
sys.modules["llm_shared"] = llm_shared

from app import research  # noqa: E402
from app.ai import _schema  # noqa: E402

MODEL = os.environ.get("LOCAL_MODEL", "qwen3.8:27b-mlx")
BASE_URL = os.environ.get("LOCAL_BASE_URL", "http://localhost:11434/v1")


LAST: dict = {}


def local_ai(user, page, kind, system, prompt, schema=None):
    llm = llm_shared.OpenAICompatibleLLM(BASE_URL, "ollama", MODEL, timeout=600)
    try:
        result = llm.complete_json(system, prompt, schema or _schema(kind), kind=kind)
    except llm_shared.LLMError as exc:
        LAST["error"] = str(exc)
        return None, True
    LAST["raw"] = result
    return result, False


def main() -> int:
    research.run_ai = local_ai  # point the real pipeline at Ollama
    game = {"name": "Grand Theft Auto V", "slug": "grand-theft-auto-v"}
    sources, fallback = research.gather_sources(game)
    print(f"sources: {len(sources)} (fallback feed={fallback})")
    ideas, ai_fallback = research.generate_ideas(game, sources)
    print(f"model: {MODEL}  ideas: {len(ideas)}  fallback: {ai_fallback}")
    if not ideas:
        print("RAW RESULT:", json.dumps(LAST.get("raw"), indent=2)[:2000])
    for idea in ideas:
        card = idea["card"]
        print(f"- {card['hook_text']} | {card['question']}")
        for url in idea["source_urls"]:
            print(f"    {url}")
    return 0 if ideas else 1


if __name__ == "__main__":
    raise SystemExit(main())
