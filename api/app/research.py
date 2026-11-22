"""The daily research brain.

For each enabled game it pulls three free, official sources (YouTube Data API,
Reddit, gaming-news RSS), passes the raw signal to the one AI client, and stores
the result as sourced mission candidates. An idea is only stored when it cites a
real source from the feed; an idea with no source is never shown.

With no source keys (or LLM_PROVIDER=recorded, the CI mode) it runs on the saved
sample feed and marks the run as a fallback, so the whole pipeline is provable
without credentials.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import re
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zoneinfo

import jsonschema

from . import db
from .ai import run_ai
from .config import settings
from .keys import resolve
from .users import audit

CONTRACTS = pathlib.Path(__file__).resolve().parents[1] / "contracts"
if not CONTRACTS.exists():
    CONTRACTS = pathlib.Path(__file__).resolve().parents[2] / "contracts"
CARD_SCHEMA = json.loads((CONTRACTS / "mission-card.schema.json").read_text())
SAMPLE_FEED = pathlib.Path(__file__).resolve().parent / "research_sample.json"

NEWS_FEEDS = [
    "https://www.polygon.com/rss/index.xml",
    "https://kotaku.com/rss",
    "https://www.rockpapershotgun.com/feed",
    "https://www.eurogamer.net/feed",
]

SYSTEM = (
    "You write playable missions for a gameplay Shorts platform. You are given "
    "real, current sources about the game. Write ideas that answer what players "
    "are talking about right now. Every idea must cite at least one source URL "
    "from the list, using the exact URL. Never invent a source. Never use story "
    "spoilers, online cheats, or trademarked names in a title. Return JSON only."
)


# --- HTTP helpers ---------------------------------------------------------

def _get(url: str, headers: dict | None = None, timeout: int = 10):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": settings.reddit_user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _get_json(url: str, headers: dict | None = None) -> dict | None:
    try:
        return json.loads(_get(url, headers))
    except Exception:
        return None


def _get_text(url: str, headers: dict | None = None) -> str | None:
    try:
        return _get(url, headers).decode("utf-8", "replace")
    except Exception:
        return None


# --- Sources --------------------------------------------------------------

def _youtube_sources(game: dict) -> list[dict]:
    api_key = resolve("youtube")
    if not api_key:
        return []
    query = urllib.parse.quote(f"{game['name']} gameplay")
    url = (
        "https://www.googleapis.com/youtube/v3/search?part=snippet"
        f"&q={query}&order=viewCount&type=video&maxResults=10"
        f"&key={api_key}"
    )
    data = _get_json(url)
    out = []
    for item in (data or {}).get("items", []):
        video_id = (item.get("id") or {}).get("videoId")
        snippet = item.get("snippet") or {}
        if not video_id or not snippet.get("title"):
            continue
        out.append({
            "kind": "youtube",
            "title": snippet["title"],
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "external_id": video_id,
            "published_at": snippet.get("publishedAt"),
        })
    return out


def _reddit_headers() -> dict:
    """OAuth when a read-only app is configured, else the public JSON UA."""
    client_id = resolve("reddit_client")
    client_secret = resolve("reddit_secret")
    if not (client_id and client_secret):
        return {"User-Agent": settings.reddit_user_agent}
    try:
        import base64

        token = _post_form(
            "https://www.reddit.com/api/v1/access_token",
            {"grant_type": "client_credentials"},
            headers={
                "User-Agent": settings.reddit_user_agent,
                "Authorization": "Basic "
                + base64.b64encode(
                    f"{client_id}:{client_secret}".encode()
                ).decode(),
            },
        )
        access = (token or {}).get("access_token")
        if access:
            return {"User-Agent": settings.reddit_user_agent, "Authorization": f"Bearer {access}"}
    except Exception:
        pass
    return {"User-Agent": settings.reddit_user_agent}


def _post_form(url: str, form: dict, headers: dict | None = None) -> dict | None:
    try:
        data = urllib.parse.urlencode(form).encode()
        req = urllib.request.Request(url, data=data, headers=headers or {})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.load(resp)
    except Exception:
        return None


def _reddit_sources(game: dict) -> list[dict]:
    sub = re.sub(r"[^a-zA-Z0-9]", "", game["slug"]) or "gaming"
    headers = _reddit_headers()
    data = _get_json(f"https://www.reddit.com/r/{sub}/hot.json?limit=10", headers)
    if not data:
        query = urllib.parse.quote(game["name"])
        data = _get_json(f"https://www.reddit.com/search.json?q={query}&sort=hot&limit=10", headers)
    out = []
    for child in (data or {}).get("data", {}).get("children", []):
        post = child.get("data") or {}
        permalink = post.get("permalink")
        title = post.get("title")
        if not permalink or not title:
            continue
        out.append({
            "kind": "reddit",
            "title": title,
            "url": f"https://www.reddit.com{permalink}",
            "external_id": post.get("id"),
            "published_at": (
                datetime.datetime.fromtimestamp(
                    post["created_utc"], datetime.timezone.utc
                ).isoformat()
                if post.get("created_utc") else None
            ),
        })
    return out


def _news_sources(game: dict) -> list[dict]:
    name = game["name"].lower()
    out = []
    for feed in NEWS_FEEDS:
        text = _get_text(feed)
        if not text:
            continue
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            continue
        for item in root.iter():
            if not item.tag.lower().endswith("item"):
                continue
            title = next((c.text for c in item if c.tag.lower().endswith("title")), "") or ""
            link = next((c.text for c in item if c.tag.lower().endswith("link")), "") or ""
            desc = next((c.text for c in item if c.tag.lower().endswith("description")), "") or ""
            if name in title.lower() or name in desc.lower():
                out.append({
                    "kind": "news",
                    "title": title.strip()[:200],
                    "url": link.strip(),
                    "external_id": None,
                    "published_at": None,
                })
            if len(out) >= 10:
                return out
    return out


def sample_feed() -> list[dict]:
    data = json.loads(SAMPLE_FEED.read_text())
    return data.get("sources", [])


def gather_sources(game: dict) -> tuple[list[dict], bool]:
    """Return (sources, used_fallback). Never raises."""
    live_keys = bool(
        resolve("youtube") or (resolve("reddit_client") and resolve("reddit_secret"))
    )
    if settings.llm_provider == "recorded" or not live_keys:
        return sample_feed(), True

    sources: list[dict] = []
    for fetch in (_youtube_sources, _reddit_sources, _news_sources):
        try:
            sources.extend(fetch(game))
        except Exception:
            continue
    # Deduplicate by URL, keeping the first (most specific) source.
    seen = set()
    unique = []
    for source in sources:
        url = source.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        unique.append(source)
    return unique, False


# --- Idea generation ------------------------------------------------------

def generate_ideas(game: dict, sources: list[dict]) -> tuple[list[dict], bool]:
    """Return (ideas, fallback). Each idea carries only verified source URLs.

    Sources are cited by short id (`s1`, `s2`, …), not by long URL: models copy
    short ids reliably and mangle long URLs, and an id that is not in the feed
    is dropped.
    """
    if not sources:
        return [], False
    labelled = [{**s, "id": f"s{i + 1}"} for i, s in enumerate(sources)]
    prompt = (
        f"Game: {game['name']}\n\nSources (cite their id exactly, e.g. s1):\n"
        + json.dumps(
            [
                {"id": s["id"], "kind": s["kind"], "title": s["title"], "url": s["url"]}
                for s in labelled
            ],
            ensure_ascii=False,
        )
    )
    result, fallback = run_ai({"id": None}, "research", "research", SYSTEM, prompt)
    if fallback or not result:
        return [], True

    known = {s["id"]: s for s in labelled}
    ideas = []
    for raw in (result or {}).get("ideas", []):
        raw = dict(raw)
        cited_ids = [i for i in raw.pop("source_ids", []) if i in known]
        if not cited_ids:
            continue  # accuracy: an idea with no real source is not shown
        cited = [known[i]["url"] for i in cited_ids]
        card = {
            "question": raw.get("question", ""),
            "hook_text": raw.get("hook_text", ""),
            "setup": raw.get("setup", ""),
            "win_condition": raw.get("win_condition", ""),
            "result_type": raw.get("result_type", ""),
            "est_minutes": raw.get("est_minutes", 8),
            "title_options": raw.get("title_options", []),
            "mode": raw.get("mode", "free_roam"),
        }
        try:
            jsonschema.validate(card, {**CARD_SCHEMA, "required": [
                k for k in CARD_SCHEMA["required"]
                if k not in ("id", "status", "evidence", "policy")
            ]})
        except jsonschema.ValidationError:
            continue
        ideas.append({"card": card, "source_urls": cited})
    return ideas, False


def _new_id(game_id: str, question: str, salt: int = 0) -> str:
    digest = hashlib.sha256(f"{game_id}:{question}:{salt}".encode()).hexdigest()
    return f"m_{int(digest, 16) % 100_000_000:08d}"


def store_ideas(game_id: str, ideas: list[dict], sources: list[dict]) -> int:
    known = {s["url"]: s for s in sources}
    stored = 0
    with db.session() as conn:
        with conn.cursor() as cur:
            for idea in ideas:
                card = dict(idea["card"])
                for salt in range(1000):
                    card["id"] = _new_id(game_id, card["question"], salt)
                    cur.execute("SELECT 1 FROM missions WHERE id = %s", (card["id"],))
                    if cur.fetchone() is None:
                        break
                card["status"] = "unverified"
                card["evidence"] = {
                    "askers": 0,
                    "source_video_ids": [known[u].get("external_id") for u in idea["source_urls"] if known[u].get("external_id")],
                }
                card["policy"] = {"spoiler": False, "online_exploit": False}
                jsonschema.validate(card, CARD_SCHEMA)
                cur.execute(
                    "INSERT INTO missions (id, card, status, game_id) "
                    "VALUES (%s, %s, 'candidate', %s) "
                    "ON CONFLICT (id) DO UPDATE SET card = EXCLUDED.card, game_id = EXCLUDED.game_id",
                    (card["id"], json.dumps(card), game_id),
                )
                for url in idea["source_urls"]:
                    source = known[url]
                    cur.execute(
                        "INSERT INTO mission_sources (mission_id, kind, title, url, external_id, published_at) "
                        "VALUES (%s, %s, %s, %s, %s, %s) "
                        "ON CONFLICT DO NOTHING",
                        (
                            card["id"], source["kind"], source["title"], source["url"],
                            source.get("external_id"), source.get("published_at"),
                        ),
                    )
                stored += 1
    return stored


# --- Runs -----------------------------------------------------------------

RESEARCH_STAGES = ("fetch", "write", "store")


def _game_by_id(game_id: str) -> dict:
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, slug, name, genre, release_date, art_url FROM games WHERE id = %s",
                (game_id,),
            )
            row = cur.fetchone()
    if row is None:
        raise ValueError("game not found")
    return {
        "id": str(row[0]), "slug": row[1], "name": row[2],
        "genre": row[3],
        "release_date": row[4].isoformat() if row[4] else None,
        "art_url": row[5],
    }


def _start_run(game_id: str) -> str:
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO research_runs (game_id, status, stage, detail) "
                "VALUES (%s, 'running', 'queued', 'Waiting for a worker…') RETURNING id",
                (game_id,),
            )
            return str(cur.fetchone()[0])


def _set_stage(run_id: str, stage: str, detail: str) -> None:
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE research_runs SET stage = %s, detail = %s WHERE id = %s",
                (stage, detail, run_id),
            )


def execute_research(run_id: str, game_id: str, actor_id: str | None) -> dict:
    """The pipeline, writing its stage as it moves. Raises on failure."""
    game = _game_by_id(game_id)
    started = time.monotonic()
    counts: dict[str, int] = {}
    try:
        _set_stage(run_id, "fetch", "Fetching YouTube, Reddit and gaming news…")
        sources, fallback = gather_sources(game)
        for source in sources:
            counts[source["kind"]] = counts.get(source["kind"], 0) + 1
        _set_stage(
            run_id, "write",
            f"{len(sources)} sources fetched — the AI is writing ideas…",
        )
        ideas, ai_fallback = generate_ideas(game, sources)
        _set_stage(run_id, "store", f"Storing {len(ideas)} sourced idea(s)…")
        stored = store_ideas(game_id, ideas, sources) if ideas else 0
        result = {
            "run_id": run_id,
            "game_id": game_id,
            "sources": counts,
            "ideas": stored,
            "fallback": fallback or ai_fallback,
            "latency_ms": int((time.monotonic() - started) * 1000),
        }
        _finish_run(run_id, "done", counts, stored, result["fallback"], None)
        audit(actor_id, "research.run", "game", game_id, result)
        return result
    except Exception as exc:
        _finish_run(run_id, "failed", counts, 0, False, str(exc))
        raise


def run_research(game_id: str, actor_id: str | None = None) -> dict:
    """Synchronous run, used by the daily loop."""
    _game_by_id(game_id)
    return execute_research(_start_run(game_id), game_id, actor_id)


def start_research(game_id: str, actor_id: str | None = None) -> dict:
    """Start a run in the background and return at once, so the admin can watch
    it move through fetch → write → store instead of waiting on a blocking call."""
    _game_by_id(game_id)
    run_id = _start_run(game_id)
    threading.Thread(
        target=execute_research,
        args=(run_id, game_id, actor_id),
        name=f"research-{run_id}",
        daemon=True,
    ).start()
    return {"run_id": run_id, "status": "running", "stage": "queued"}


def _serialize_run(r) -> dict:
    return {
        "id": str(r[0]),
        "game_id": str(r[1]),
        "game_name": r[2],
        "status": r[3],
        "stage": r[4],
        "detail": r[5],
        "source_counts": r[6],
        "ideas_count": r[7],
        "fallback": r[8],
        "error": r[9],
        "created_at": r[10].isoformat() if r[10] else None,
        "finished_at": r[11].isoformat() if r[11] else None,
    }


def get_run(run_id: str) -> dict | None:
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT r.id, r.game_id, g.name, r.status, r.stage, r.detail, "
                "r.source_counts, r.ideas_count, r.fallback, r.error, "
                "r.created_at, r.finished_at "
                "FROM research_runs r JOIN games g ON g.id = r.game_id WHERE r.id = %s",
                (run_id,),
            )
            row = cur.fetchone()
    return _serialize_run(row) if row else None


def recent_runs(limit: int = 10) -> list[dict]:
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT r.id, r.game_id, g.name, r.status, r.stage, r.detail, "
                "r.source_counts, r.ideas_count, r.fallback, r.error, "
                "r.created_at, r.finished_at "
                "FROM research_runs r JOIN games g ON g.id = r.game_id "
                "ORDER BY r.created_at DESC LIMIT %s",
                (limit,),
            )
            rows = cur.fetchall()
    return [_serialize_run(r) for r in rows]


def _finish_run(run_id: str, status: str, counts: dict, ideas: int, fallback: bool, error: str | None):
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE research_runs SET status = %s, source_counts = %s, ideas_count = %s, "
                "fallback = %s, error = %s, finished_at = now() WHERE id = %s",
                (status, json.dumps(counts), ideas, fallback, error, run_id),
            )


def _now() -> datetime.datetime:
    try:
        return datetime.datetime.now(zoneinfo.ZoneInfo(settings.research_timezone))
    except Exception:
        return datetime.datetime.now(datetime.timezone.utc)


def _past_scheduled_hour() -> bool:
    return _now().hour >= settings.research_hour


def daily_research() -> list[str]:
    """Run today's research for every enabled game that has not run yet.

    Idempotent: the date gate is a database read, so a second API replica (or a
    restart) does not produce a second run. Returns the game ids that ran.
    """
    ran = []
    if not _past_scheduled_hour():
        return ran
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM games WHERE enabled = true ORDER BY created_at")
            game_ids = [str(r[0]) for r in cur.fetchall()]
    today = _now().date().isoformat()
    for game_id in game_ids:
        try:
            with db.session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT 1 FROM research_runs WHERE game_id = %s AND created_at::date = %s LIMIT 1",
                        (game_id, today),
                    )
                    if cur.fetchone() is not None:
                        continue
            run_research(game_id)
            ran.append(game_id)
        except Exception:
            continue
    return ran


def _source(r) -> dict:
    return {
        "kind": r[0],
        "title": r[1],
        "url": r[2],
        "external_id": r[3],
        "published_at": r[4].isoformat() if r[4] else None,
    }


def sources_map(cur, mission_ids: list[str]) -> dict[str, list[dict]]:
    """All sources for a page of missions in one query (a per-row query would
    cost one Neon round trip each)."""
    if not mission_ids:
        return {}
    cur.execute(
        "SELECT mission_id, kind, title, url, external_id, published_at FROM mission_sources "
        "WHERE mission_id = ANY(%s) ORDER BY mission_id, created_at",
        (mission_ids,),
    )
    out: dict[str, list[dict]] = {}
    for r in cur.fetchall():
        out.setdefault(r[0], []).append(_source(r[1:]))
    return out


def card_with_sources(cur, mission_id: str) -> dict:
    """A mission plus its real sources. Used by the dare editor."""
    cur.execute("SELECT id, card, status, score FROM missions WHERE id = %s", (mission_id,))
    row = cur.fetchone()
    if row is None:
        return {}
    return {
        "id": row[0],
        "card": row[1],
        "status": row[2],
        "score": row[3],
        "sources": sources_map(cur, [mission_id]).get(mission_id, []),
    }


def start_scheduler() -> None:
    """A small DB-gated daily loop. No extra dependency; the date gate makes it
    safe to run in every API replica."""
    import threading

    def loop():
        while True:
            try:
                daily_research()
            except Exception:
                pass
            time.sleep(300)

    threading.Thread(target=loop, name="research-scheduler", daemon=True).start()
