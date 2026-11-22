"""Missions: the LLM writes cards, an editor approves them, a creator accepts."""
from __future__ import annotations

import datetime
import hashlib
import html
import json
import pathlib
import re
import time

import jsonschema
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

from . import db
from .ai import run_ai
from .paging import envelope, order_clause, parse
from .research import card_with_sources, sources_map
from .users import audit, current_user, require_admin

router = APIRouter()

CONTRACTS = pathlib.Path(__file__).resolve().parents[1] / "contracts"
if not CONTRACTS.exists():
    CONTRACTS = pathlib.Path(__file__).resolve().parents[2] / "contracts"
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
    game_id = request.query_params.get("game_id")
    q = (request.query_params.get("q") or "").strip()
    source = request.query_params.get("source")
    min_score = request.query_params.get("min_score")
    where = "m.status = %s"
    params: list = [status]
    if game_id:
        where += " AND m.game_id = %s"
        params.append(game_id)
    if q:
        where += " AND (m.card->>'question' ILIKE %s OR m.card->>'hook_text' ILIKE %s)"
        params += [f"%{q}%", f"%{q}%"]
    if source:
        where += (
            " AND EXISTS (SELECT 1 FROM mission_sources s "
            "WHERE s.mission_id = m.id AND s.kind = %s)"
        )
        params.append(source)
    if min_score:
        try:
            where += " AND m.score >= %s"
            params.append(float(min_score))
        except ValueError:
            pass
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM missions m WHERE {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"SELECT m.id, m.card, m.score, m.status FROM missions m WHERE {where} "
                f"ORDER BY {order_clause(sort, POOL_SORT, 'm.created_at', order)} "
                f"LIMIT %s OFFSET %s",
                params + [size, (page - 1) * size],
            )
            rows = cur.fetchall()
            sources = sources_map(cur, [r[0] for r in rows])
            items = []
            for r in rows:
                entry = _card(r)
                entry["sources"] = sources.get(r[0], [])
                items.append(entry)
    return envelope(items, total, page, size)


@router.post("/admin/pool/bulk", dependencies=[Depends(require_admin)])
def pool_bulk(request: Request, payload: dict):
    """One transaction for many ideas: approve, reject or assign."""
    user = current_user(request)
    ids = payload.get("ids") or []
    action = payload.get("action")
    if not isinstance(ids, list) or not ids or action not in ("approve", "reject", "assign"):
        raise HTTPException(422, "ids and a valid action are required")
    user_id = payload.get("user_id")
    updated = 0
    with db.session() as conn:
        with conn.cursor() as cur:
            if action == "assign":
                if not user_id:
                    raise HTTPException(422, "user_id is required to assign")
                cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
                if cur.fetchone() is None:
                    raise HTTPException(404, "gamer not found")
                today = datetime.date.today()
                for mission_id in ids:
                    cur.execute("SELECT id FROM missions WHERE id = %s", (mission_id,))
                    if cur.fetchone() is None:
                        continue
                    cur.execute(
                        "INSERT INTO assignments (user_id, mission_id, date, state) "
                        "VALUES (%s, %s, %s, 'assigned') ON CONFLICT DO NOTHING",
                        (user_id, mission_id, today),
                    )
                    updated += 1
            else:
                target = "unverified" if action == "approve" else "rejected"
                for mission_id in ids:
                    cur.execute(
                        "UPDATE missions SET status = %s "
                        "WHERE id = %s AND status = 'candidate' RETURNING id",
                        (target, mission_id),
                    )
                    if cur.fetchone() is not None:
                        updated += 1
    audit(user["id"], f"pool.bulk.{action}", "mission", "", {"count": updated})
    return {"updated": updated}


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


def _wrap(text: str, width: int) -> list[str]:
    words, lines, line = text.split(), [], ""
    for word in words:
        if len(line) + len(word) + 1 > width and line:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines


_CARD_CACHE: dict[str, tuple[float, str]] = {}
_CARD_TTL = 60.0


def _card_svg(card: dict, game_name: str) -> str:
    """Render the idea's visual identity as an SVG. No remote image."""
    hook = html.escape(card.get("hook_text", ""))
    question = html.escape(card.get("question", ""))
    win = html.escape(card.get("win_condition", ""))
    mode = html.escape(card.get("mode", ""))
    title = html.escape((card.get("title_options") or [""])[0])
    game = html.escape(game_name)
    mission_id = html.escape(str(card.get("id", "")))

    hook_lines = _wrap(hook.upper(), 16)[:3]
    question_lines = _wrap(question, 26)
    win_lines = _wrap(win, 30)

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">',
        '<rect width="1080" height="1920" fill="#050505"/>',
        '<rect x="24" y="24" width="1032" height="1872" rx="48" fill="none" stroke="#C8FF3D" stroke-width="3"/>',
        f'<text x="90" y="220" font-family="Verdana, sans-serif" font-size="30" letter-spacing="8" fill="#8B7CFF">{game.upper()[:30]}</text>',
    ]
    y = 330
    for line in hook_lines:
        parts.append(
            f'<text x="90" y="{y}" font-family="Verdana, sans-serif" font-size="96" '
            f'font-weight="bold" fill="#C8FF3D">{line}</text>'
        )
        y += 104
    y += 20
    parts.append(
        f'<text x="90" y="{y}" font-family="Verdana, sans-serif" font-size="44" fill="#FAFAFA">{title[:60]}</text>'
    )
    y += 90
    for line in question_lines:
        parts.append(
            f'<text x="90" y="{y}" font-family="Verdana, sans-serif" font-size="42" fill="#FAFAFA">{line}</text>'
        )
        y += 52
    y += 40
    for line in win_lines:
        parts.append(
            f'<text x="90" y="{y}" font-family="Verdana, sans-serif" font-size="34" fill="#A3A3A3">{line}</text>'
        )
        y += 44
    parts.append(
        f'<text x="90" y="1740" font-family="Verdana, sans-serif" font-size="30" letter-spacing="4" '
        f'fill="#737373">{mode.upper()} · {mission_id}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


@router.get("/missions/{mission_id}/card.svg")
def mission_card_svg(mission_id: str):
    # The card is a pure function of the mission, so a short cache keeps the
    # image off the critical path on warm loads.
    now = time.time()
    hit = _CARD_CACHE.get(mission_id)
    if hit and now - hit[0] < _CARD_TTL:
        return Response(content=hit[1], media_type="image/svg+xml")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT m.card, g.name FROM missions m LEFT JOIN games g ON g.id = m.game_id "
                "WHERE m.id = %s",
                (mission_id,),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "mission not found")
    svg = _card_svg(row[0], row[1] or "")
    _CARD_CACHE[mission_id] = (now, svg)
    return Response(content=svg, media_type="image/svg+xml")


@router.get("/missions/{mission_id}")
def get_mission(mission_id: str):
    with db.session() as conn:
        with conn.cursor() as cur:
            entry = card_with_sources(cur, mission_id)
    if not entry:
        raise HTTPException(404, "mission not found")
    return entry


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
    _CARD_CACHE.pop(mission_id, None)
    audit(user["id"], "mission.update", "mission", mission_id)
    return {"id": mission_id, "card": card}


@router.get("/today")
def today(request: Request):
    user = current_user(request)
    date = datetime.date.today()
    with db.session() as conn:
        with conn.cursor() as cur:
            # One round trip for the dares and this user's assignments.
            cur.execute(
                "SELECT m.id, m.card, m.score, m.status, a.id, a.state "
                "FROM missions m "
                "LEFT JOIN assignments a "
                "  ON a.mission_id = m.id AND a.user_id = %s AND a.date = %s "
                "WHERE m.status = 'unverified' ORDER BY m.id",
                (user["id"], date),
            )
            joined = cur.fetchall()
            cur.execute(
                "SELECT m.card->>'mode' FROM clips c "
                "JOIN assignments a ON a.id = c.assignment_id "
                "JOIN missions m ON m.id = a.mission_id "
                "WHERE a.user_id = %s GROUP BY 1 ORDER BY count(*) DESC LIMIT 1",
                (user["id"],),
            )
            preferred = cur.fetchone()
    rows: list = []
    accepted: dict[str, str] = {}
    assignments: list[dict] = []
    seen: set = set()
    for r in joined:
        if r[0] not in seen:
            seen.add(r[0])
            rows.append(r)
        if r[4]:
            accepted[r[0]] = r[5]
            assignments.append({"id": str(r[4]), "mission_id": r[0], "state": r[5]})

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
