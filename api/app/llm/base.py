from abc import ABC, abstractmethod

from llm_shared import LLMError

__all__ = ["LLM", "LLMError"]


class LLM(ABC):
    """One provider behind one interface. Nothing else imports a vendor SDK."""

    @abstractmethod
    def complete_json(self, system: str, user: str, schema: dict | None = None, kind: str | None = None) -> dict:
        """Return a JSON object. `schema`, when given, must be satisfied."""
