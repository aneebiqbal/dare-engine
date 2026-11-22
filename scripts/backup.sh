#!/usr/bin/env bash
# Back up the database. Prefers a local pg_dump against DATABASE_URL_DIRECT;
# falls back to the compose db container. Writes a timestamped gzip and never
# prints the connection string.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p backups

# Load DATABASE_URL_DIRECT / DATABASE_URL from .env without exporting the value.
DB_URL=""
if [ -f .env ]; then
  DB_URL="$(grep -E '^DATABASE_URL_DIRECT=' .env | tail -1 | cut -d= -f2-)"
  [ -n "$DB_URL" ] || DB_URL="$(grep -E '^DATABASE_URL=' .env | tail -1 | cut -d= -f2-)"
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="backups/clipdesk-${STAMP}.sql.gz"

if [ -n "$DB_URL" ] && command -v pg_dump >/dev/null 2>&1; then
  pg_dump --no-owner --no-privileges "$DB_URL" | gzip > "$OUT"
elif docker compose ps db --format '{{.State}}' 2>/dev/null | grep -q running; then
  docker compose exec -T db sh -c \
    'pg_dump --no-owner --no-privileges -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$OUT"
else
  echo "No DATABASE_URL and no running db container. Set DATABASE_URL_DIRECT or start the stack." >&2
  exit 1
fi

echo "wrote $OUT ($(du -h "$OUT" | cut -f1))"
echo "keep the last N:  ls -t backups | tail -n +8 | xargs -r rm --"
