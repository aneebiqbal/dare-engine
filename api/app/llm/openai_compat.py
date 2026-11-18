"""The OpenAI-compatible client lives in `shared/llm.py` so the API and the
worker use exactly the same code. This module re-exports it."""

from llm_shared import LLMError, OpenAICompatibleLLM

__all__ = ["LLMError", "OpenAICompatibleLLM"]
