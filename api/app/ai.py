"""AI on every page, through one client, with schema validation, one retry,
usage logging and a visible non-AI fallback."""
from __future__ import annotations

import json
import pathlib

from fastapi import APIRouter, HTTPException, Request

from . import db
from .llm import LLMError, get_llm
from .users import current_user

router = APIRouter()

# Docker copies contracts next to the app package; the repo keeps them at the
# root. Resolve whichever exists so the app also runs from a local checkout.
CONTRACTS = pathlib.Path(__file__).resolve().parents[1] / "contracts"
if not CONTRACTS.exists():
    CONTRACTS = pathlib.Path(__file__).resolve().parents[2] / "contracts"
CARD_SCHEMA = json.loads((CONTRACTS / "mission-card.schema.json").read_text())
GUIDE = (pathlib.Path(__file__).resolve().parent / "help_guide.md").read_text()

FALLBACK_NOTICE = "AI is unavailable, so this used a non-AI fallback."


def _schema(kind: str) -> dict | None:
    if kind == "cards":
        return {"type": "object", "properties": {"cards": {"type": "array", "items": CARD_SCHEMA}}, "required": ["cards"]}
    if kind == "suggest":
        return {"type": "object", "properties": {"cards": {"type": "array", "items": CARD_SCHEMA, "maxItems": 3}}, "required": ["cards"]}
    if kind == "editor":
        return {
            "type": "object",
            "properties": {
                "hook_text": {"type": "string"},
                "win_condition": {"type": "string"},
                "title_spoiler": {"type": "boolean"},
            },
            "required": ["hook_text", "win_condition"],
        }
    if kind == "clip_review":
        return {
            "type": "object",
            "properties": {
                "hook_line": {"type": "string"},
                "score": {"type": "number"},
                "weaknesses": {"type": "array", "items": {"type": "string"}},
                "beats": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["hook_line", "score", "weaknesses"],
        }
    if kind == "export":
        return {
            "type": "object",
            "properties": {
                "titles": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 3},
                "description": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["titles", "description", "tags"],
        }
    if kind == "results_summary":
        return {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}
    if kind == "pool_review":
        return {
            "type": "object",
            "properties": {
                "merged": {"type": "array", "items": {"type": "object"}},
                "policy_flags": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["merged", "policy_flags"],
        }
    if kind == "help":
        return {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]}
    if kind == "research":
        idea = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "question": {"type": "string", "minLength": 10, "maxLength": 200},
                "hook_text": {"type": "string", "minLength": 3, "maxLength": 40},
                "setup": {"type": "string", "minLength": 5, "maxLength": 300},
                "win_condition": {"type": "string", "minLength": 5, "maxLength": 300},
                "result_type": {"type": "string", "enum": ["time_seconds", "star_count", "pass_fail", "distance_meters", "cash_dollars"]},
                "est_minutes": {"type": "integer", "minimum": 1, "maximum": 30},
                "title_options": {"type": "array", "minItems": 1, "maxItems": 3, "items": {"type": "string", "minLength": 5, "maxLength": 100}},
                "mode": {"type": "string", "enum": ["free_roam", "race", "mission_replay"]},
                "source_ids": {"type": "array", "minItems": 1, "maxItems": 5, "items": {"type": "string", "minLength": 1}},
            },
            "required": ["question", "hook_text", "setup", "win_condition", "result_type", "est_minutes", "title_options", "mode", "source_ids"],
        }
        return {"type": "object", "properties": {"ideas": {"type": "array", "items": idea, "maxItems": 10}}, "required": ["ideas"]}
    return None


def run_ai(user: dict, page: str, kind: str, system: str, prompt: str, schema: dict | None = None):
    """Return (result, fallback). Never raises: a failure is a visible fallback."""
    llm = get_llm()
    try:
        result = llm.complete_json(system, prompt, schema or _schema(kind), kind=kind)
        fallback = False
    except LLMError:
        result, fallback = None, True
    usage = getattr(llm, "last_usage", {})
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO ai_usage (user_id, page, kind, provider, model, "
                "prompt_tokens, completion_tokens, latency_ms, fallback) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    user["id"], page, kind,
                    usage.get("provider", getattr(llm, "provider", "unknown")),
                    usage.get("model", getattr(llm, "model", "")),
                    usage.get("prompt_tokens", 0),
                    usage.get("completion_tokens", 0),
                    usage.get("latency_ms", 0),
                    fallback,
                ),
            )
    return result, fallback


def _clip_rows(cur, user_id: str, clip_id: str | None = None):
    cur.execute(
        "SELECT c.id, c.title, c.transcript, c.state, m.card "
        "FROM clips c JOIN assignments a ON a.id = c.assignment_id "
        "JOIN missions m ON m.id = a.mission_id "
        "WHERE a.user_id = %s" + (" AND c.id = %s" if clip_id else ""),
        (user_id, clip_id) if clip_id else (user_id,),
    )
    return cur.fetchall()


@router.post("/ai/suggest")
def suggest(request: Request, payload: dict):
    user = current_user(request)
    mission_id = payload.get("mission_id", "")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT card FROM missions WHERE id = %s", (mission_id,))
            liked = cur.fetchone()
            cur.execute(
                "SELECT id, card FROM missions WHERE status = 'unverified' AND id <> %s ORDER BY id",
                (mission_id,),
            )
            pool = [{"id": r[0], "card": r[1]} for r in cur.fetchall()]
    liked_card = liked[0] if liked else None
    if liked_card is None:
        raise HTTPException(404, "mission not found")

    system = (
        "You recommend gameplay missions similar to one a creator liked. "
        "Return JSON only."
    )
    prompt = (
        f"Liked mission: {liked_card.get('question', '')} "
        f"(mode {liked_card.get('mode', '')}). "
        f"Candidate missions: {json.dumps([p['card'].get('question', '') for p in pool])}"
    )
    result, fallback = run_ai(user, "today", "suggest", system, prompt)
    if fallback or not result:
        # Deterministic non-AI fallback: the next three approved missions.
        suggestions = [p["card"] for p in pool[:3]]
        return {"suggestions": suggestions, "fallback": True, "notice": FALLBACK_NOTICE}
    cards = result.get("cards", [])[:3]
    return {"suggestions": cards, "fallback": False}


@router.post("/ai/mission-editor")
def mission_editor(request: Request, payload: dict):
    user = current_user(request)
    card = payload.get("card") or {}
    field = payload.get("field", "hook")
    if field not in ("hook", "win_condition", "title"):
        raise HTTPException(422, "field must be hook, win_condition or title")
    system = (
        "You edit gameplay mission cards. Tighten the hook and the win condition, "
        "and check the title for story spoilers and trademarked names. Return JSON only."
    )
    prompt = f"Card: {json.dumps(card)}\nField to improve: {field}"
    result, fallback = run_ai(user, "mission-editor", "editor", system, prompt)
    if fallback or not result:
        return {
            "hook_text": card.get("hook_text", ""),
            "win_condition": card.get("win_condition", ""),
            "title_spoiler": False,
            "fallback": True,
            "notice": FALLBACK_NOTICE,
        }
    return {**result, "fallback": False}


@router.post("/ai/clip-review")
def clip_review(request: Request, payload: dict):
    user = current_user(request)
    clip_id = payload.get("clip_id")
    with db.session() as conn:
        with conn.cursor() as cur:
            rows = _clip_rows(cur, user["id"], clip_id)
    if not rows:
        raise HTTPException(404, "clip not found")
    _cid, title, transcript, state, card = rows[0]
    words = [w.get("text", "") for w in (transcript or [])][:400]
    system = (
        "You review a finished gameplay Short. Choose the strongest hook line, "
        "score it out of 100 and name what is weak. Return JSON only."
    )
    prompt = f"Mission: {card.get('question', '')}\nHook: {card.get('hook_text', '')}\nTranscript: {' '.join(words)}"
    result, fallback = run_ai(user, "clips", "clip_review", system, prompt)
    if fallback or not result:
        # Non-AI fallback: score from transcript length and state only.
        score = 60 if words else 30
        return {
            "hook_line": card.get("hook_text", ""),
            "score": score,
            "weaknesses": ["AI review unavailable; check the captions by eye."] if not words else [],
            "beats": [],
            "fallback": True,
            "notice": FALLBACK_NOTICE,
        }
    return {**result, "fallback": False}


@router.post("/ai/export")
def export_copy(request: Request, payload: dict):
    user = current_user(request)
    clip_id = payload.get("clip_id")
    with db.session() as conn:
        with conn.cursor() as cur:
            rows = _clip_rows(cur, user["id"], clip_id)
    if not rows:
        raise HTTPException(404, "clip not found")
    _cid, title, transcript, state, card = rows[0]
    system = (
        "You write YouTube Shorts metadata. Write three title options, a "
        "description and tags. Never use trademarked names in a title. Return JSON only."
    )
    prompt = f"Mission: {card.get('question', '')}\nHook: {card.get('hook_text', '')}\nExisting title: {title or ''}"
    result, fallback = run_ai(user, "export", "export", system, prompt)
    if fallback or not result:
        question = card.get("question", "Mission")
        return {
            "titles": [question, card.get("hook_text", ""), f"{question} — mission"],
            "description": f"{question}\n\nMission {card.get('id', '')}.",
            "tags": ["clipdesk", "missions", card.get("mode", "")],
            "fallback": True,
            "notice": FALLBACK_NOTICE,
        }
    return {**result, "fallback": False}


@router.get("/ai/results-summary")
def results_summary(request: Request):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT m.card->>'mode', COUNT(c.id), COALESCE(SUM(mm.views), 0) "
                "FROM clips c JOIN assignments a ON a.id = c.assignment_id "
                "JOIN missions m ON m.id = a.mission_id "
                "LEFT JOIN posts p ON p.clip_id = c.id "
                "LEFT JOIN metrics mm ON mm.post_id = p.id "
                "WHERE a.user_id = %s GROUP BY m.card->>'mode'",
                (user["id"],),
            )
            by_type = [{"mode": r[0], "clips": r[1], "views": int(r[2] or 0)} for r in cur.fetchall()]
            cur.execute(
                "SELECT c.title, COALESCE(SUM(m.views), 0) FROM clips c "
                "JOIN assignments a ON a.id = c.assignment_id "
                "LEFT JOIN posts p ON p.clip_id = c.id "
                "LEFT JOIN metrics m ON m.post_id = p.id "
                "WHERE a.user_id = %s GROUP BY c.id, c.title ORDER BY c.created_at DESC LIMIT 5",
                (user["id"],),
            )
            top = [{"title": r[0], "views": int(r[1] or 0)} for r in cur.fetchall()]
    system = (
        "You summarise which mission types and layouts are working for a creator. "
        "Cite the numbers you used. Return JSON only."
    )
    prompt = f"By mission type: {json.dumps(by_type)}\nTop clips: {json.dumps(top)}"
    result, fallback = run_ai(user, "results", "results_summary", system, prompt)
    if fallback or not result:
        best = max(by_type, key=lambda r: r["views"], default=None)
        summary = (
            f"Best performing type: {best['mode']} with {best['views']} views across {best['clips']} clips."
            if best
            else "No results recorded yet."
        )
        return {"summary": summary, "fallback": True, "notice": FALLBACK_NOTICE, "by_type": by_type}
    return {**result, "fallback": False, "by_type": by_type}


@router.post("/ai/pool-review")
def pool_review(request: Request, payload: dict):
    user = current_user(request)
    questions = payload.get("questions") or []
    if not questions:
        raise HTTPException(422, "no questions supplied")
    system = (
        "You merge duplicate audience questions and flag policy problems "
        "(story spoilers, online cheats, unsafe titles). Return JSON only."
    )
    prompt = f"Questions: {json.dumps(questions)}"
    result, fallback = run_ai(user, "admin-pool", "pool_review", system, prompt)
    if fallback or not result:
        merged = [{"question": q, "count": 1} for q in questions]
        return {"merged": merged, "policy_flags": [], "fallback": True, "notice": FALLBACK_NOTICE}
    return {**result, "fallback": False}


@router.get("/help/guide")
def help_guide():
    return {"guide": GUIDE}


@router.post("/ai/help")
def help_answer(request: Request, payload: dict):
    user = current_user(request)
    question = (payload.get("question") or "").strip()
    if not question:
        raise HTTPException(422, "question required")
    system = (
        "You answer 'how do I' questions about Clipdesk using ONLY the guide "
        "below. If the guide does not answer it, say so. Return JSON only.\n\n"
        f"GUIDE:\n{GUIDE}"
    )
    result, fallback = run_ai(user, "help", "help", system, question)
    if fallback or not result:
        return {"answer": "AI help is unavailable right now. Open the guide from the Help page.", "fallback": True, "notice": FALLBACK_NOTICE}
    return {**result, "fallback": False}
