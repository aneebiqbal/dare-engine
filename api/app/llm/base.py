from abc import ABC, abstractmethod


class LLM(ABC):
    """One provider behind one interface. Nothing else in the app imports a vendor SDK."""

    @abstractmethod
    def complete_json(self, system: str, user: str, schema: dict | None = None) -> dict:
        """Return a JSON object. `schema`, when given, is a JSON Schema the result must satisfy."""
