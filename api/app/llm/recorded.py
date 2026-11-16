import json

from .base import LLM


class RecordedLLM(LLM):
    """Replays a captured response file so CI never needs a live call or a key.

    The file holds a list of JSON objects; each call takes the next one, wrapping
    around. Responses are fixtures, not production data.
    """

    def __init__(self, path: str):
        with open(path) as fh:
            responses = json.load(fh)
        if isinstance(responses, dict):
            responses = [responses]
        self._responses = responses
        self._i = 0

    def complete_json(self, system: str, user: str, schema: dict | None = None) -> dict:
        response = self._responses[self._i % len(self._responses)]
        self._i += 1
        return response
