#!/usr/bin/env bash
# Start teorell live stack: FastAPI (WS) + Vite React UI.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
  UVICORN="$ROOT/.venv/bin/uvicorn"
elif command -v uvicorn >/dev/null 2>&1; then
  PYTHON="${PYTHON:-python3}"
  UVICORN="uvicorn"
else
  echo "error: install the live extras first:" >&2
  echo "  python3 -m venv .venv && source .venv/bin/activate && pip install -e \".[live]\"" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "error: npm is required (Node.js)" >&2
  exit 1
fi

if [[ ! -d "$ROOT/apps/web/node_modules" ]]; then
  echo "Installing web dependencies…"
  (cd "$ROOT/apps/web" && npm install)
fi

API_PID=""
WEB_PID=""

cleanup() {
  trap - EXIT INT TERM
  if [[ -n "$WEB_PID" ]] && kill -0 "$WEB_PID" 2>/dev/null; then
    kill "$WEB_PID" 2>/dev/null || true
    wait "$WEB_PID" 2>/dev/null || true
  fi
  if [[ -n "$API_PID" ]] && kill -0 "$API_PID" 2>/dev/null; then
    kill "$API_PID" 2>/dev/null || true
    wait "$API_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "API  → http://127.0.0.1:${API_PORT}  (ws /ws)"
echo "UI   → http://localhost:${WEB_PORT}"
echo "Ctrl+C stops both."
echo

export PYTHONPATH="${ROOT}/src:${ROOT}${PYTHONPATH:+:$PYTHONPATH}"

"$UVICORN" apps.api.main:app --reload --host 127.0.0.1 --port "$API_PORT" &
API_PID=$!

(cd "$ROOT/apps/web" && npm run dev -- --port "$WEB_PORT") &
WEB_PID=$!

# If either child exits, shut down the other.
wait -n "$API_PID" "$WEB_PID"
EXIT_CODE=$?
cleanup
exit "$EXIT_CODE"
