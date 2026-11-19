"""Games: the admin grid, the game profile, and the research trigger.

A game owns ideas. The research worker writes sourced candidates per game; the
admin approves and assigns them through the existing pool flow.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Request

from . import db, research
from .research import sources_map
from .config import settings
from .paging import envelope, order_clause, parse
from .users import audit, current_user, require_admin

router = APIRouter()

GAME_SORT = {"created_at": "g.created_at", "name": "g.name", "slug": "g.slug"}

SAMPLE_GAMES = [
    {
        "slug": "grand-theft-auto-v",
        "name": "Grand Theft Auto V",
        "external_id": "9724",
        "genre": "Action",
        "release_date": "2013-09-17",
        "art_url": None,
    },
    {
        "slug": "gta-6",
        "name": "Grand Theft Auto VI",
        "external_id": "0",
        "genre": "Action",
        "release_date": None,
        "art_url": None,
    },
]


def _rawg(path: str, params: dict) -> dict | None:
    if not settings.rawg_api_key:
        return None
    params = {**params, "key": settings.rawg_api_key}
    url = f"https://api.rawg.io/api/{path}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "clipdesk-research/0.1"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.load(resp)
    except Exception:
        return None


def _rawg_search(query: str) -> list[dict]:
    data = _rawg("games", {"search": query, "page_size": 10})
    if not data:
        return [g for g in SAMPLE_GAMES if query.lower() in g["name"].lower()] or SAMPLE_GAMES[:1]
    out = []
    for game in data.get("results", []):
        out.append({
            "slug": game.get("slug"),
            "name": game.get("name"),
            "external_id": str(game.get("id")) if game.get("id") is not None else None,
            "genre": (game.get("genres") or [{}])[0].get("name"),
            "release_date": game.get("released"),
            "art_url": game.get("background_image"),
        })
    return out


def _rawg_details(external_id: str) -> dict:
    data = _rawg(f"games/{external_id}", {})
    if not data:
        return {}
    return {
        "genre": (data.get("genres") or [{}])[0].get("name"),
        "release_date": data.get("released"),
        "art_url": data.get("background_image"),
    }


def _game_row(cur, game_id: str):
    cur.execute(
        "SELECT id, slug, name, external_id, source, genre, release_date, art_url, enabled, created_at "
        "FROM games WHERE id = %s",
        (game_id,),
    )
    return cur.fetchone()


def _serialize(row) -> dict:
    return {
        "id": str(row[0]),
        "slug": row[1],
        "name": row[2],
        "external_id": row[3],
        "source": row[4],
        "genre": row[5],
        "release_date": row[6].isoformat() if row[6] else None,
        "art_url": row[7],
        "enabled": row[8],
        "created_at": row[9].isoformat(),
    }


@router.get("/admin/games", dependencies=[Depends(require_admin)])
def list_games(request: Request):
    page, size, sort, order = parse(request, "created_at")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM games")
            total = cur.fetchone()[0]
            cur.execute(
                "SELECT g.id, g.slug, g.name, g.external_id, g.source, g.genre, g.release_date, "
                "g.art_url, g.enabled, g.created_at "
                f"FROM games g ORDER BY {order_clause(sort, GAME_SORT, 'g.created_at', order)} "
                "LIMIT %s OFFSET %s",
                (size, (page - 1) * size),
            )
            rows = cur.fetchall()
            games = [_serialize(r) for r in rows]
            ids = [g["id"] for g in games]
            counts: dict[str, dict[str, int]] = {}
            gamers: dict[str, set[str]] = {}
            if ids:
                cur.execute(
                    "SELECT game_id, status, count(*) FROM missions "
                    "WHERE game_id = ANY(%s) GROUP BY game_id, status",
                    (ids,),
                )
                for game_id, status, n in cur.fetchall():
                    counts.setdefault(str(game_id), {})[status] = n
                cur.execute(
                    "SELECT DISTINCT m.game_id, a.user_id FROM assignments a "
                    "JOIN missions m ON m.id = a.mission_id WHERE m.game_id = ANY(%s)",
                    (ids,),
                )
                for game_id, user_id in cur.fetchall():
                    gamers.setdefault(str(game_id), set()).add(str(user_id))
            for game in games:
                game["candidates"] = counts.get(game["id"], {}).get("candidate", 0)
                game["approved"] = counts.get(game["id"], {}).get("unverified", 0)
                game["gamers"] = len(gamers.get(game["id"], ()))
    return envelope(games, total, page, size)


@router.post("/admin/games/search", dependencies=[Depends(require_admin)])
def search_games(request: Request, payload: dict):
    query = (payload.get("query") or "").strip()
    if not query:
        raise HTTPException(422, "query required")
    return {"results": _rawg_search(query)}


@router.post("/admin/games", dependencies=[Depends(require_admin)])
def create_game(request: Request, payload: dict):
    user = current_user(request)
    slug = (payload.get("slug") or "").strip()
    name = (payload.get("name") or "").strip()
    if not slug or not name:
        raise HTTPException(422, "slug and name required")

    genre = payload.get("genre")
    release_date = payload.get("release_date")
    art_url = payload.get("art_url")
    external_id = payload.get("external_id")
    # Auto-build the profile from the games database when the caller only has an
    # external id (the admin grid's "add from search" path).
    if external_id and not (genre and release_date and art_url):
        details = _rawg_details(str(external_id))
        genre = genre or details.get("genre")
        release_date = release_date or details.get("release_date")
        art_url = art_url or details.get("art_url")

    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO games (slug, name, external_id, source, genre, release_date, art_url) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (slug) DO NOTHING RETURNING id",
                (slug, name, external_id, payload.get("source") or "rawg", genre, release_date, art_url),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(409, "a game with that slug already exists")
            game_id = str(row[0])
    audit(user["id"], "game.create", "game", game_id, {"slug": slug, "name": name})
    return {"id": game_id, "slug": slug, "name": name}


@router.get("/admin/games/{game_id}", dependencies=[Depends(require_admin)])
def game_profile(request: Request, game_id: str):
    with db.session() as conn:
        with conn.cursor() as cur:
            row = _game_row(cur, game_id)
            if row is None:
                raise HTTPException(404, "game not found")
            game = _serialize(row)
            cur.execute(
                "SELECT id, card, score, status FROM missions WHERE game_id = %s AND status = 'candidate' "
                "ORDER BY created_at DESC LIMIT 50",
                (game_id,),
            )
            candidate_rows = cur.fetchall()
            cur.execute(
                "SELECT id, card, score, status FROM missions WHERE game_id = %s AND status = 'unverified' "
                "ORDER BY created_at DESC LIMIT 50",
                (game_id,),
            )
            approved_rows = cur.fetchall()
            sources = sources_map(
                cur, [r[0] for r in candidate_rows] + [r[0] for r in approved_rows]
            )
            candidates = [
                {
                    "id": r[0], "card": r[1], "score": r[2],
                    "status": r[3], "state": r[3], "sources": sources.get(r[0], []),
                }
                for r in candidate_rows
            ]
            approved = [
                {
                    "id": r[0], "card": r[1], "score": r[2],
                    "status": r[3], "state": r[3], "sources": sources.get(r[0], []),
                }
                for r in approved_rows
            ]
            cur.execute(
                "SELECT a.id, a.user_id, a.state, a.date, u.display_name, m.id "
                "FROM assignments a JOIN missions m ON m.id = a.mission_id "
                "JOIN users u ON u.id = a.user_id "
                "WHERE m.game_id = %s ORDER BY a.created_at DESC LIMIT 50",
                (game_id,),
            )
            assigned = [
                {
                    "assignment_id": str(r[0]),
                    "user_id": str(r[1]),
                    "display_name": r[4] or "Creator",
                    "state": r[2],
                    "date": r[3].isoformat(),
                    "mission_id": r[5],
                }
                for r in cur.fetchall()
            ]
            cur.execute(
                "SELECT id, status, source_counts, ideas_count, fallback, error, created_at, finished_at "
                "FROM research_runs WHERE game_id = %s ORDER BY created_at DESC LIMIT 10",
                (game_id,),
            )
            runs = [
                {
                    "id": str(r[0]),
                    "status": r[1],
                    "source_counts": r[2],
                    "ideas_count": r[3],
                    "fallback": r[4],
                    "error": r[5],
                    "created_at": r[6].isoformat(),
                    "finished_at": r[7].isoformat() if r[7] else None,
                }
                for r in cur.fetchall()
            ]
    return {"game": game, "candidates": candidates, "approved": approved, "assigned": assigned, "runs": runs}


@router.patch("/admin/games/{game_id}", dependencies=[Depends(require_admin)])
def update_game(request: Request, game_id: str, payload: dict):
    user = current_user(request)
    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        raise HTTPException(422, "enabled must be a boolean")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE games SET enabled = %s WHERE id = %s RETURNING id", (enabled, game_id))
            if cur.fetchone() is None:
                raise HTTPException(404, "game not found")
    audit(user["id"], "game.update", "game", game_id, {"enabled": enabled})
    return {"id": game_id, "enabled": enabled}


@router.post("/admin/games/{game_id}/research", dependencies=[Depends(require_admin)])
def run_game_research(request: Request, game_id: str):
    user = current_user(request)
    try:
        result = research.run_research(game_id, actor_id=user["id"])
    except ValueError:
        raise HTTPException(404, "game not found")
    return result


@router.get("/games")
def list_enabled_games(request: Request):
    current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, slug, name, genre, release_date, art_url FROM games "
                "WHERE enabled = true ORDER BY name"
            )
            rows = cur.fetchall()
    return [
        {
            "id": str(r[0]),
            "slug": r[1],
            "name": r[2],
            "genre": r[3],
            "release_date": r[4].isoformat() if r[4] else None,
            "art_url": r[5],
        }
        for r in rows
    ]
