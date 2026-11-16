"""Gemini over its REST API, so no vendor SDK is needed.

The key is read from GEMINI_API_KEY and never logged.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

DEFAULT_MODEL = "gemini-2.0-flash"
TIMEOUT = 60


class GeminiLLM:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self._key = api_key
        self._model = model

    def complete_json(self, system: str, user: str, schema: dict | None = None) -> dict:
        prompt = f"{system}\n\n{user}\n\nReturn JSON only."
        if schema:
            prompt += f"\nSchema: {json.dumps(schema)}"
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent?key={self._key}"
        )
        req = urllib.request.Request(
            url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = json.load(resp)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Gemini HTTP {exc.code}") from None
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Gemini unreachable: {exc.reason}") from None
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
