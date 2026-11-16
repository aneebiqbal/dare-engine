from .base import LLM


class StubLLM(LLM):
    """Fails loudly. Never invents a response in a production code path."""

    def complete_json(self, system: str, user: str, schema: dict | None = None) -> dict:
        raise RuntimeError(
            "No LLM provider configured. Set LLM_PROVIDER=gemini and provide a key, "
            "or LLM_PROVIDER=recorded with LLM_RECORDED_RESPONSE for tests."
        )
