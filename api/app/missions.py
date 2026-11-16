"""Missions: the LLM writes cards, an editor approves them, a creator accepts."""
from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import re

import jsonschema
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import db
from .llm import get_llm
from .users import current_user

router = APIRouter()

CONTRACTS = pathlib.Path(__file__).resolve().parents[1] / "contracts"
CARD_SCHEMA = json.loads((CONTRACTS / "mission-card.schema.json").read_text())
_ID = re.compile(r"^m_[0-9]{4,}$")

SYSTEM = (
    "You write playable missions for a gameplay Shorts platform. Each mission "
    "answers one public question about the game. It must be playable in free "
    "roam, in under ten minutes, with a clear win condition and a measurable "
    "result. Never use story spoilers, online cheats, or trademarked names in a "
    "title. Return JSON only."
)
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {"cards": {"type": "array", "items": CARD_SCHEMA}},
    "required": ["cards"],
}


class QuestionsIn(BaseModel):
    questions: list[str]


class MissionIn(BaseModel):
    mission_id: str


class SwapIn(BaseModel):
    mission_id: str


def _card(row) -> dict:
    return {"id": row[0], "card": row[1], "score": row[2], "state": row[3]}


@router.post("/admin/questions")
def write_cards(payload: QuestionsIn):
    current_user()
    if not payload.questions:
        raise HTTPException(422, "no questions supplied")

    result = get_llm().complete_json(
        SYSTEM, json.dumps(payload.questions), RESPONSE_SCHEMA
    )
    cards = result.get("cards", [])
    if not cards:
        raise HTTPException(422, "the model returned no cards")

    stored = []
    with db.session() as conn:
        with conn.cursor() as cur:
            for i, card in enumerate(cards):
                card = dict(card)
                if not _ID.match(str(card.get("id", ""))):
                    card["id"] = f"m_{1000 + i:04d}"
                jsonschema.validate(card, CARD_SCHEMA)
                cur.execute(
                    "INSERT INTO missions (id, card, status) VALUES (%s, %s, 'candidate') "
                    "ON CONFLICT (id) DO UPDATE SET card = EXCLUDED.card",
                    (card["id"], json.dumps(card)),
                )
                stored.append(card)
    return {"cards": stored, "count": len(stored)}


@router.get("/admin/pool")
def pool():
    current_user()
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, card, score, status FROM missions "
                "WHERE status = 'candidate' ORDER BY created_at"
            )
            return [_card(r) for r in cur.fetchall()]


@router.post("/admin/pool/{mission_id}/approve")
def approve(mission_id: str):
    current_user()
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE missions SET status = 'unverified' "
                "WHERE id = %s AND status = 'candidate' RETURNING id",
                (mission_id,),
            )
            if cur.fetchone() is None:
                raise HTTPException(404, "not a candidate")
    return {"id": mission_id, "state": "unverified"}


@router.get("/today")
def today():
    user = current_user()
    date = datetime.date.today()
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, card, score, status FROM missions "
                "WHERE status = 'unverified' ORDER BY id"
            )
            rows = cur.fetchall()
            cur.execute(
                "SELECT mission_id, state FROM assignments "
                "WHERE user_id = %s AND date = %s",
                (user["id"], date),
            )
            accepted = {r[0]: r[1] for r in cur.fetchall()}

    if not rows:
        return {"date": date.isoformat(), "daily": None, "picks": [], "accepted": accepted}

    pick = int(hashlib.sha256(date.isoformat().encode()).hexdigest(), 16) % len(rows)
    daily = _card(rows[pick])
    picks = [_card(r) for r in rows[:3]]
    return {
        "date": date.isoformat(),
        "daily": daily["card"],
        "picks": [p["card"] for p in picks],
        "accepted": accepted,
    }


@router.post("/assignments")
def accept(payload: MissionIn):
    user = current_user()
    date = datetime.date.today()
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO assignments (user_id, mission_id, date, state) "
                "VALUES (%s, %s, %s, 'accepted') "
                "ON CONFLICT DO NOTHING RETURNING id",
                (user["id"], payload.mission_id, date),
            )
            row = cur.fetchone()
    return {"id": str(row[0]) if row else None, "mission_id": payload.mission_id, "state": "accepted"}


@router.post("/assignments/{assignment_id}/swap")
def swap(assignment_id: str, payload: SwapIn):
    user = current_user()
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE assignments SET mission_id = %s, state = 'swapped' "
                "WHERE id = %s AND user_id = %s RETURNING id",
                (payload.mission_id, assignment_id, user["id"]),
            )
            if cur.fetchone() is None:
                raise HTTPException(404, "assignment not found")
    return {"id": assignment_id, "mission_id": payload.mission_id, "state": "swapped"}
