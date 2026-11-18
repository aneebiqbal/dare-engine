"""One OpenAI-compatible chat client, shared by the API and the worker.

Configured only by base URL, API key, model and timeout. Calls ask for JSON,
validate against a schema, retry once on invalid output, and report usage
through an optional callback so both services log tokens and latency.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

import jsonschema


class LLMError(RuntimeError):
    """The provider failed or returned something invalid for the schema."""


class OpenAICompatibleLLM:
    provider = "openai"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: int = 60,
        log_usage=None,
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key or ""
        self.model = model or ""
        self.timeout = timeout
        self._log_usage = log_usage
        self.last_usage: dict = {}

    def _report(self, kind, started, fallback, prompt_tokens=0, completion_tokens=0):
        self.last_usage = {
            "provider": self.provider,
            "model": self.model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "latency_ms": int((time.monotonic() - started) * 1000),
        }
        if self._log_usage is not None:
            self._log_usage(
                kind=kind,
                provider=self.provider,
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=self.last_usage["latency_ms"],
                fallback=fallback,
            )

    def _post(self, messages: list[dict]) -> dict:
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            detail = exc.read()[:500].decode(errors="replace")
            raise LLMError(f"LLM HTTP {exc.code}: {detail}") from None
        except urllib.error.URLError as exc:
            raise LLMError(f"LLM unreachable: {exc.reason}") from None

    @staticmethod
    def _parse(data: dict) -> dict:
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("LLM returned no message content") from exc
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM returned invalid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise LLMError("LLM returned JSON that is not an object")
        return parsed

    def complete_json(self, system: str, user: str, schema: dict | None = None, kind: str | None = None) -> dict:
        prompt = f"{system}\n\n{user}\n\nReturn JSON only."
        if schema:
            prompt += f"\nSchema: {json.dumps(schema)}"

        started = time.monotonic()
        last_error: Exception | None = None
        for attempt in range(2):  # one retry on invalid output
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user if attempt == 0 else prompt},
            ]
            if attempt == 1:
                messages.append(
                    {"role": "user", "content": "Your last answer was not valid JSON for the schema. Return only valid JSON."}
                )
            try:
                data = self._post(messages)
                parsed = self._parse(data)
                if schema is not None:
                    jsonschema.validate(parsed, schema)
                usage = data.get("usage") or {}
                self._report(
                    kind, started, False,
                    int(usage.get("prompt_tokens") or 0),
                    int(usage.get("completion_tokens") or 0),
                )
                return parsed
            except LLMError as exc:
                last_error = exc
            except jsonschema.ValidationError as exc:
                last_error = LLMError(f"schema mismatch: {exc.message}")
        self._report(kind, started, True)
        raise last_error or LLMError("LLM call failed")
