from ..config import settings
from .base import LLM, LLMError
from .recorded import RecordedLLM
from .stub import StubLLM


def get_llm() -> LLM:
    provider = (settings.llm_provider or "").lower()
    if provider == "openai":
        from .openai_compat import OpenAICompatibleLLM

        return OpenAICompatibleLLM(
            settings.llm_base_url, settings.llm_api_key, settings.llm_model, settings.llm_timeout
        )
    if provider == "recorded":
        return RecordedLLM(settings.llm_recorded_response)
    return StubLLM()


__all__ = ["LLM", "LLMError", "get_llm"]
