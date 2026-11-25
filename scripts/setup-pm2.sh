#!/usr/bin/env bash
# One-time PM2 host setup: Python venv, API deps, and the shared-module shims
# the images provide next to the app package.
#
#   scripts/setup-pm2.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null || { echo "python3 not found" >&2; exit 1; }

if [ ! -x .venv/bin/python ]; then
  "$PY" -m venv .venv
  .venv/bin/pip install --upgrade pip >/dev/null
  .venv/bin/pip install -q -r api/requirements.txt
else
  # Existing venv: only repair it, never churn pins on a running host.
  if ! .venv/bin/python -c "import fastapi, uvicorn, psycopg" >/dev/null 2>&1; then
    .venv/bin/pip install -q -r api/requirements.txt
  fi
fi

mkdir -p .pm2/py
cp -f shared/llm.py .pm2/py/llm_shared.py
cp -f shared/key_crypto.py .pm2/py/key_crypto.py
cp -f shared/platforms.py .pm2/py/platforms.py
# The API reads clip templates beside its package (the image copies this too).
cp -f worker/clip/templates.json api/app/clip_templates.json

echo "API ready. Next: scripts/build-web-standalone.sh && pm2 start ecosystem.config.cjs"
