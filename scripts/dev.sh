#!/usr/bin/env bash
# Local development: Flask API on :5000 and the static frontend on :8000.
# Usage: scripts/dev.sh   (Ctrl-C stops both)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="$ROOT/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "No .venv found. Create it with:"
  echo "  uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements-dev.txt"
  exit 1
fi

export FLASK_ENV="${FLASK_ENV:-development}"
export PORT="${PORT:-5000}"
FRONTEND_PORT="${FRONTEND_PORT:-8000}"

[ -f .env ] && echo "Loading .env" || echo "No .env file (mock fallbacks active). See .env.example"

"$PY" app.py &
BACKEND_PID=$!
"$PY" -m http.server "$FRONTEND_PORT" --bind 127.0.0.1 &
FRONTEND_PID=$!

cleanup() {
  echo
  echo "Stopping backend ($BACKEND_PID) and frontend ($FRONTEND_PID)..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "Backend:  http://localhost:$PORT/health"
echo "Frontend: http://localhost:$FRONTEND_PORT/"
echo "Dev sign-in (no Firebase keys): POST /auth/dev-login {email}. Seeded accounts:"
echo "  client@lineup.dev  (uid client_1, role client, 3 credits)"
echo "  barber@lineup.dev  (uid barber_1, role barber, shop \"Mike's Cuts\", free plan)"
echo "Set LINEUP_DEV_SECRET in .env to keep dev tokens valid across restarts."
wait
