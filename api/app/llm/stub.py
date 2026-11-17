from .base import LLM, LLMError


class StubLLM(LLM):
    """Fails loudly. Never invents a response in a production code path."""

    provider = "stub"

    def complete_json(self, system: str, user: str, schema: dict | None = None, kind: str | None = None) -> dict:
        raise LLMError(
            "No LLM provider configured. Set LLM_BASE_URL, LLM_API_KEY and "
            "LLM_MODEL, or LLM_PROVIDER=recorded with LLM_RECORDED_RESPONSE."
        )
