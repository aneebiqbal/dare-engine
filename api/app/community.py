"""Community: public mission pages, leaderboards and creator profiles."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from . import db
from .paging import envelope, order_clause, parse

router = APIRouter()


def _card(cur, mission_id):
    cur.execute("SELECT card FROM missions WHERE id = %s", (mission_id,))
    row = cur.fetchone()
    return row[0] if row else None


@router.get("/m/{slug}")
def mission_page(slug: str):
    with db.session() as conn:
        with conn.cursor() as cur:
            card = _card(cur, slug)
            if card is None:
                raise HTTPException(404, "mission not found")
            cur.execute(
                "SELECT a.rank, a.user_id, a.result_value, a.clip_id "
                "FROM (SELECT user_id, result_value, clip_id, "
                "             row_number() OVER (ORDER BY result_value ASC NULLS LAST) AS rank "
                "      FROM attempts WHERE mission_id = %s) a "
                "ORDER BY a.rank",
                (slug,),
            )
            attempts = [
                {"rank": r[0], "user_id": str(r[1]), "result_value": r[2], "clip_id": str(r[3]) if r[3] else None}
                for r in cur.fetchall()
            ]
    return {"slug": slug, "card": card, "attempts": attempts}


@router.get("/missions/{mission_id}/leaderboard")
def leaderboard(request: Request, mission_id: str):
    page, size, sort, order = parse(request, "rank", "asc")
    allowed = {"rank": "result_value", "result_value": "result_value", "user_id": "user_id"}
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM attempts WHERE mission_id = %s", (mission_id,))
            total = cur.fetchone()[0]
            cur.execute(
                "SELECT user_id, result_value, clip_id FROM attempts "
                f"WHERE mission_id = %s ORDER BY {order_clause(sort, allowed, 'result_value', order)} "
                "LIMIT %s OFFSET %s",
                (mission_id, size, (page - 1) * size),
            )
            rows = cur.fetchall()
    return envelope(
        [
            {"rank": i, "user_id": str(r[0]), "result_value": r[1], "clip_id": str(r[2]) if r[2] else None}
            for i, r in enumerate(rows, (page - 1) * size + 1)
        ],
        total,
        page,
        size,
    )


@router.get("/creators/{user_id}")
def creator(request: Request, user_id: str):
    page, size, sort, order = parse(request, "created_at")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM attempts WHERE user_id = %s", (user_id,))
            total = cur.fetchone()[0]
            cur.execute(
                "SELECT a.mission_id, a.result_value, a.clip_id, m.card FROM attempts a "
                "JOIN missions m ON m.id = a.mission_id "
                f"WHERE a.user_id = %s ORDER BY {order_clause(sort, {'created_at': 'a.created_at', 'result_value': 'a.result_value'}, 'a.created_at', order)} "
                "LIMIT %s OFFSET %s",
                (user_id, size, (page - 1) * size),
            )
            rows = cur.fetchall()
    return envelope(
        [
            {
                "mission_id": r[0],
                "result_value": r[1],
                "clip_id": str(r[2]) if r[2] else None,
                "card": r[3],
            }
            for r in rows
        ],
        total,
        page,
        size,
    )
