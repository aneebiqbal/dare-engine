# The research brain

The brain turns a game into a queue of playable, sourced ideas. It runs once a
day per enabled game and on demand from the admin game profile.

## Sources

Three independent free sources, so no single outage stops a run:

| Source | Key | What it finds |
| --- | --- | --- |
| YouTube Data API v3 | `YOUTUBE_API_KEY` | The ten most-viewed videos for `<game> gameplay` right now. |
| Reddit | `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` (optional; public JSON with a User-Agent otherwise) | Hot posts from the game's subreddit, falling back to a Reddit search. |
| Gaming news RSS | none | Recent items from Polygon, Kotaku, Rock Paper Shotgun and Eurogamer that mention the game. |

With no keys (or `LLM_PROVIDER=recorded`, the CI mode) the brain runs on
`api/app/research_sample.json` and flags the run `fallback: true`. Nothing is
presented as live.

## Pipeline

1. `gather_sources(game)` fetches and de-duplicates the sources.
2. The one AI client (`shared/llm.py`) is asked for ideas and must cite source
   ids (`s1`, `s2`, …) from the feed. The response is validated against a schema.
   Ids, not URLs: a model copies a short id reliably and mangles a long URL.
3. Each idea's ids are resolved against the fetched feed. An idea with no real
   source is dropped — it is never shown.
4. Surviving ideas are stored as `missions` rows (`status='candidate'`,
   `game_id`) plus `mission_sources` rows, and a `research_runs` row records the
   source counts, idea count and whether it was a fallback.
5. The admin approves/rejects/assigns from the game profile or the pool. Only
   an approved idea reaches a gamer's Today.

## Scheduling

`RESEARCH_ENABLED` (default true) starts a small DB-gated loop in the API. Every
five minutes it runs research for each enabled game that has no run today, but
only after `RESEARCH_HOUR` in `RESEARCH_TIMEZONE`. The date gate is a database
read, so a second replica or a restart does not produce a duplicate run.

## Run it

```sh
# on demand, from the API container
curl -X POST localhost:8000/admin/games/<game_id>/research ...

# or from the admin: Games → the game → Research now
```

## Tests

- `tests/unit/test_research.py` — citation filtering, schema validation,
  fallback, sample feed.
- `tests/acceptance/test_games_research.py` — game → research → sourced
  candidates → approve → assign → gamer Today, on the real stack.
