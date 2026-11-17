from abc import ABC, abstractmethod


class LLMError(RuntimeError):
    """The provider failed or returned something that is not valid for the schema."""


class LLM(ABC):
    """One provider behind one interface. Nothing else imports a vendor SDK."""

    provider = "abstract"
    model = ""

    @abstractmethod
    def complete_json(self, system: str, user: str, schema: dict | None = None, kind: str | None = None) -> dict:
        """Return a JSON object. `schema`, when given, must be satisfied."""
