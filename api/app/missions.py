"""Missions: the LLM writes cards, an editor approves them, a creator accepts."""
from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import re

import jsonschema
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from . import db
from .ai import run_ai
from .paging import envelope, order_clause, parse
from .users import audit, current_user, require_admin

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

POOL_SORT = {"created_at": "m.created_at", "id": "m.id", "score": "m.score"}


class QuestionsIn(BaseModel):
    questions: list[str]


class MissionIn(BaseModel):
    mission_id: str


class SwapIn(BaseModel):
    mission_id: str


class CardIn(BaseModel):
    card: dict


class AssignIn(BaseModel):
    user_id: str


def _card(row) -> dict:
    return {"id": row[0], "card": row[1], "score": row[2], "state": row[3]}


@router.post("/admin/questions", dependencies=[Depends(require_admin)])
def write_cards(request: Request, payload: QuestionsIn):
    user = current_user(request)
    if not payload.questions:
        raise HTTPException(422, "no questions supplied")

    result, fallback = run_ai(
        user, "admin-pool", "cards", SYSTEM, json.dumps(payload.questions)
    )
    cards = (result or {}).get("cards", []) if not fallback else []
    if not cards:
        # Non-AI fallback: a plain card per question, clearly marked.
        cards = [
            {
                "id": f"m_{2000 + i:04d}",
                "question": q[:200],
                # The schema caps hook_text at 40 chars.
                "hook_text": q[:40],
                "setup": "Play the mission in free roam.",
                "win_condition": "Complete the mission and record the result.",
                "result_type": "pass_fail",
                "est_minutes": 8,
                "title_options": [q[:100]],
                "mode": "free_roam",
                "status": "unverified",
                "evidence": {"askers": 0, "source_video_ids": []},
                "policy": {"spoiler": False, "online_exploit": False},
            }
            for i, q in enumerate(payload.questions)
        ]

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
    audit(user["id"], "questions.write", "mission", "", {"count": len(stored), "fallback": fallback})
    return {"cards": stored, "count": len(stored), "fallback": fallback}


@router.get("/admin/pool", dependencies=[Depends(require_admin)])
def pool(request: Request):
    page, size, sort, order = parse(request, "created_at")
    status = request.query_params.get("status", "candidate")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM missions WHERE status = %s", (status,))
            total = cur.fetchone()[0]
            cur.execute(
                f"SELECT m.id, m.card, m.score, m.status FROM missions m WHERE m.status = %s "
                f"ORDER BY {order_clause(sort, POOL_SORT, 'm.created_at', order)} "
                f"LIMIT %s OFFSET %s",
                (status, size, (page - 1) * size),
            )
            rows = cur.fetchall()
    return envelope([_card(r) for r in rows], total, page, size)


@router.post("/admin/pool/{mission_id}/approve", dependencies=[Depends(require_admin)])
def approve(request: Request, mission_id: str):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE missions SET status = 'unverified' "
                "WHERE id = %s AND status = 'candidate' RETURNING id",
                (mission_id,),
            )
            if cur.fetchone() is None:
                raise HTTPException(404, "not a candidate")
    audit(user["id"], "pool.approve", "mission", mission_id)
    return {"id": mission_id, "state": "unverified"}


@router.post("/admin/pool/{mission_id}/reject", dependencies=[Depends(require_admin)])
def reject(request: Request, mission_id: str):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE missions SET status = 'rejected' "
                "WHERE id = %s AND status = 'candidate' RETURNING id",
                (mission_id,),
            )
            if cur.fetchone() is None:
                raise HTTPException(404, "not a candidate")
    audit(user["id"], "pool.reject", "mission", mission_id)
    return {"id": mission_id, "state": "rejected"}


@router.post("/admin/pool/{mission_id}/assign", dependencies=[Depends(require_admin)])
def assign(request: Request, mission_id: str, payload: AssignIn):
    """Give a approved dare to one gamer's Today."""
    user = current_user(request)
    date = datetime.date.today()
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id = %s", (payload.user_id,))
            if cur.fetchone() is None:
                raise HTTPException(404, "user not found")
            cur.execute("SELECT id FROM missions WHERE id = %s", (mission_id,))
            if cur.fetchone() is None:
                raise HTTPException(404, "mission not found")
            cur.execute(
                "INSERT INTO assignments (user_id, mission_id, date, state) "
                "VALUES (%s, %s, %s, 'assigned') "
                "ON CONFLICT DO NOTHING RETURNING id",
                (payload.user_id, mission_id, date),
            )
            row = cur.fetchone()
    audit(user["id"], "pool.assign", "mission", mission_id, {"user_id": payload.user_id})
    return {"id": str(row[0]) if row else None, "mission_id": mission_id, "state": "assigned"}


@router.get("/missions/{mission_id}")
def get_mission(mission_id: str):
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, card, score, status FROM missions WHERE id = %s", (mission_id,))
            row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "mission not found")
    return _card(row)


@router.patch("/missions/{mission_id}")
def update_mission(request: Request, mission_id: str, payload: CardIn):
    user = current_user(request)
    card = dict(payload.card)
    card["id"] = mission_id
    jsonschema.validate(card, CARD_SCHEMA)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE missions SET card = %s WHERE id = %s RETURNING id",
                (json.dumps(card), mission_id),
            )
            if cur.fetchone() is None:
                raise HTTPException(404, "mission not found")
    audit(user["id"], "mission.update", "mission", mission_id)
    return {"id": mission_id, "card": card}


@router.get("/today")
def today(request: Request):
    user = current_user(request)
    date = datetime.date.today()
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, card, score, status FROM missions "
                "WHERE status = 'unverified' ORDER BY id"
            )
            rows = cur.fetchall()
            cur.execute(
                "SELECT id, mission_id, state FROM assignments "
                "WHERE user_id = %s AND date = %s",
                (user["id"], date),
            )
            assignment_rows = cur.fetchall()
            cur.execute(
                "SELECT m.card->>'mode' FROM clips c "
                "JOIN assignments a ON a.id = c.assignment_id "
                "JOIN missions m ON m.id = a.mission_id "
                "WHERE a.user_id = %s GROUP BY 1 ORDER BY count(*) DESC LIMIT 1",
                (user["id"],),
            )
            preferred = cur.fetchone()
    accepted = {r[1]: r[2] for r in assignment_rows}
    assignments = [
        {"id": str(r[0]), "mission_id": r[1], "state": r[2]} for r in assignment_rows
    ]

    if not rows:
        return {
            "date": date.isoformat(),
            "daily": None,
            "picks": [],
            "accepted": accepted,
            "assignments": assignments,
        }

    pick = int(hashlib.sha256(date.isoformat().encode()).hexdigest(), 16) % len(rows)
    daily = _card(rows[pick])

    preferred_mode = preferred[0] if preferred else None
    rest = [r for r in rows if r[0] != daily["id"]]
    if preferred_mode:
        rest.sort(key=lambda r: (r[1].get("mode") != preferred_mode, r[0]))
    # With a single approved dare there is nothing else to pick; keep the daily
    # in the list so Today still has a card to act on.
    picks = [_card(r) for r in (rest[:3] or rows[:3])]
    return {
        "date": date.isoformat(),
        "daily": daily["card"],
        "picks": [p["card"] for p in picks],
        "accepted": accepted,
        "assignments": assignments,
    }


@router.post("/assignments")
def accept(request: Request, payload: MissionIn):
    user = current_user(request)
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
def swap(request: Request, assignment_id: str, payload: SwapIn):
    user = current_user(request)
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


@router.get("/me")
def me(request: Request):
    return {"user": current_user(request), "channels": []}
