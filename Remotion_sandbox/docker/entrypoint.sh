#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${REMOTION_APP_DIR:-/workspace/app}"

mkdir -p \
  "${APP_DIR}" \
  /workspace/storage/output \
  /workspace/storage/assets \
  /root/.cache/remotion \
  /root/.npm

cd "${APP_DIR}"

if [ ! -d node_modules ] || [ -z "$(ls -A node_modules 2>/dev/null)" ]; then
  npm install
fi

npx remotion browser ensure

exec "$@"
