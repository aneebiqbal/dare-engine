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

if [ -x .venv/bin/python ] && .venv/bin/python -c "import sys" >/dev/null 2>&1; then
  # Existing working venv: only repair it, never churn pins on a running host.
  if ! .venv/bin/python -c "import fastapi, uvicorn, psycopg" >/dev/null 2>&1; then
    .venv/bin/pip install -q -r api/requirements.txt
  fi
else
  # A failed create can leave a broken .venv behind; clear it before retry.
  rm -rf .venv
  if ! "$PY" -m venv .venv; then
    cat >&2 <<'EOF'
python3-venv is unavailable and this host has no root.
Use the user-space route in docs/deploy-web.md §2 ("No root / managed VPS"):
  micromamba create -p ~/clipdesk-py python=3.12 pip
  ~/clipdesk-py/bin/pip install -r api/requirements.txt
  mkdir -p .venv/bin && ln -s ~/clipdesk-py/bin/python .venv/bin/python
Then run scripts/setup-pm2.sh again.
EOF
    exit 3
  fi
  .venv/bin/pip install --upgrade pip >/dev/null
  .venv/bin/pip install -q -r api/requirements.txt
fi

mkdir -p .pm2/py
cp -f shared/llm.py .pm2/py/llm_shared.py
cp -f shared/key_crypto.py .pm2/py/key_crypto.py
cp -f shared/platforms.py .pm2/py/platforms.py
# The API reads clip templates beside its package (the image copies this too).
cp -f worker/clip/templates.json api/app/clip_templates.json

echo "API ready. Next: scripts/build-web-standalone.sh && pm2 start ecosystem.config.cjs"
