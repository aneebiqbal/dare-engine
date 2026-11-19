from ..config import settings
from .base import LLM, LLMError
from .recorded import RecordedLLM
from .stub import StubLLM


def get_llm() -> LLM:
    from ..settings_store import get as stored

    provider = (stored("llm_provider") or settings.llm_provider or "").lower()
    if provider == "openai":
        from .openai_compat import OpenAICompatibleLLM

        return OpenAICompatibleLLM(
            stored("llm_base_url") or settings.llm_base_url,
            settings.llm_api_key,
            stored("llm_model") or settings.llm_model,
            settings.llm_timeout,
        )
    if provider == "recorded":
        return RecordedLLM(settings.llm_recorded_response)
    return StubLLM()


__all__ = ["LLM", "LLMError", "get_llm"]
