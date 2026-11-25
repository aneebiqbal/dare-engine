"""The local scoring LLM: rubric scoring + head-to-head rerank.

Ollama on the Mac serves an OpenAI-style chat API and, unlike the vision bridge,
keeps the model resident between calls — so one load serves every candidate and
the caller unloads and verifies at the end (one model resident at a time).

All guidance lives in the editable skill files under `skills/clip-scoring/`.
"""
from __future__ import annotations

import json
import pathlib
import re
import time
import urllib.error
import urllib.request

from worker_app.config import settings

DIMENSIONS = (
    "hook_strength",
    "emotional_peak",
    "payoff_delivery",
    "standalone_clarity",
    "pace_energy",
    "quotability",
    "length_fit",
)
WEIGHTS = {
    "hook_strength": 0.25,
    "emotional_peak": 0.20,
    "payoff_delivery": 0.20,
    "standalone_clarity": 0.15,
    "pace_energy": 0.10,
    "quotability": 0.05,
    "length_fit": 0.05,
}


class ScoringError(RuntimeError):
    pass


def _skill_path(name: str) -> pathlib.Path:
    local = pathlib.Path(__file__).resolve().parents[2] / "skills" / "clip-scoring"
    path = pathlib.Path(settings.skills_dir)
    if not path.exists():
        path = local
    return path / name


def load_skill(name: str) -> str:
    try:
        return _skill_path(name).read_text()
    except OSError as exc:
        raise ScoringError(f"missing skill file {name}: {exc}") from None


def _post(messages: list[dict], temperature: float, timeout: float = 300) -> str:
    body = json.dumps(
        {
            "model": settings.scoring_model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature},
        }
    ).encode()
    url = settings.ollama_url.rstrip("/") + "/api/chat"
    req = urllib.request.Request(
        url, data=body, method="POST", headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        return (data.get("message") or {}).get("content") or ""
    except urllib.error.HTTPError as exc:
        raise ScoringError(f"scoring LLM HTTP {exc.code}: {exc.read()[:300]!r}") from None
    except urllib.error.URLError as exc:
        raise ScoringError(f"scoring LLM unreachable: {exc.reason}") from None


def _parse_json(text: str) -> dict | list:
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=-1)
        if start < 0:
            raise ScoringError(f"scoring LLM did not return JSON: {text[:200]!r}")
        return json.loads(text[start:])


def _composite(scores: dict) -> float:
    total = 0.0
    for dim, weight in WEIGHTS.items():
        try:
            value = float(scores.get(dim, 0))
        except (TypeError, ValueError):
            value = 0.0
        total += max(0.0, min(10.0, value)) * weight
    return round(total * 10, 1)


def score_window(transcript: str, timeline: str, language: str) -> dict:
    """Score one candidate window against the rubric. Returns the LLM's JSON."""
    system = load_skill("prompt_score.md").replace("{rubric}", load_skill("rubric.md"))
    system = system.replace("{language}", language or "the source")
    user = (
        f"LANGUAGE: {language or 'unknown'}\n\n"
        f"TRANSCRIPT WINDOW:\n{transcript}\n\n"
        f"EVENT TIMELINE (supporting evidence):\n{timeline}"
    )
    raw = _post(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        settings.score_temperature,
    )
    data = _parse_json(raw)
    if isinstance(data, list):
        data = data[0] if data else {}
    if not isinstance(data, dict):
        raise ScoringError(f"unexpected scoring payload: {type(data).__name__}")
    scores = data.get("scores") or {}
    for dim in DIMENSIONS:
        scores.setdefault(dim, 0)
    data["scores"] = {dim: float(scores.get(dim, 0)) for dim in DIMENSIONS}
    data["composite"] = _composite(data["scores"])
    # Kill criteria are hard, whatever the composite says.
    if data["scores"]["hook_strength"] < 4 or data["scores"]["payoff_delivery"] < 4:
        data["keep"] = False
        data.setdefault(
            "reason",
            "rejected by kill criteria (weak hook or no payoff)",
        )
    elif "keep" not in data:
        data["keep"] = data["composite"] >= 60.0
    return data


def rerank(items: list[dict]) -> dict:
    """One relative-judgement call over the finalists. Returns order/drop."""
    if len(items) < 2:
        return {"order": [i["start"] for i in items], "drop": []}
    lines = []
    for item in items:
        lines.append(
            f"[{item.get('start', 0):.0f}-{item.get('end', 0):.0f}s] "
            f"label={item.get('label', '?')} hook={item.get('hook', '')!r}\n"
            f"transcript: {item.get('transcript', '')}"
        )
    system = load_skill("prompt_rerank.md")
    user = "\n\n".join(lines)
    raw = _post(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        settings.rerank_temperature,
    )
    data = _parse_json(raw)
    starts = []
    for value in data.get("order", []):
        try:
            starts.append(int(round(float(value))))
        except (TypeError, ValueError):
            continue
    drops = []
    for value in data.get("drop", []):
        try:
            drops.append(int(round(float(value))))
        except (TypeError, ValueError):
            continue
    # Never drop something the model forgot to place; keep the best-scored tail.
    known = {int(round(i["start"])) for i in items}
    for item in sorted(items, key=lambda i: i.get("composite", 0), reverse=True):
        if int(round(item["start"])) not in starts and int(round(item["start"])) not in drops:
            starts.append(int(round(item["start"])))
    return {"order": [s for s in starts if s in known], "drop": [d for d in drops if d in known]}


def unload(timeout: float = 60.0) -> bool:
    """Unload the scoring model and verify it is gone (Ollama is asynchronous)."""
    model = settings.scoring_model
    try:
        body = json.dumps({"model": model, "keep_alive": 0}).encode()
        req = urllib.request.Request(
            settings.ollama_url.rstrip("/") + "/api/generate",
            data=body, method="POST", headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
    except Exception:
        return False
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                settings.ollama_url.rstrip("/") + "/api/ps", timeout=10
            ) as resp:
                running = [m.get("name") for m in json.loads(resp.read()).get("models", [])]
            if model not in running:
                return True
        except Exception:
            return False
        time.sleep(0.5)
    return False


def available() -> bool:
    try:
        with urllib.request.urlopen(
            settings.ollama_url.rstrip("/") + "/api/tags", timeout=5
        ) as resp:
            json.loads(resp.read())
        return True
    except Exception:
        return False
