#!/usr/bin/env bash
# Build the web app for PM2/standalone serving and place static assets where
# .next/standalone/server.js expects them.
#
#   scripts/build-web-standalone.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/web"

if [ ! -d node_modules ]; then
  npm ci
else
  npm install --no-audit --no-fund
fi

rm -rf .next/standalone
NEXT_PUBLIC_DEV_AUTH="${NEXT_PUBLIC_DEV_AUTH:-0}" npm run build

cp -R .next/static .next/standalone/.next/static
cp -R public .next/standalone/public

echo "standalone build ready: web/.next/standalone"
