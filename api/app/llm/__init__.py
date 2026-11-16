from .base import LLM
from .recorded import RecordedLLM
from .stub import StubLLM


def get_llm() -> LLM:
    from . import config

    provider = config.settings.llm_provider
    if provider == "recorded":
        return RecordedLLM(config.settings.llm_recorded_response)
    if provider == "gemini":
        from .gemini import GeminiLLM

        return GeminiLLM(config.settings.gemini_api_key)
    return StubLLM()
