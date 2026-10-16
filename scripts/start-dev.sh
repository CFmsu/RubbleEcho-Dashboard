#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -x "$ROOT/backend/.venv/bin/python" ]]; then
  echo "Create the backend virtual environment first. See README.md."
  exit 1
fi

(cd "$ROOT/backend" && .venv/bin/python -m uvicorn main:app --reload --port 8080) &
BACK_PID=$!
(cd "$ROOT/frontend" && npm run dev) &
FRONT_PID=$!

echo "Backend PID $BACK_PID  http://127.0.0.1:8080"
echo "Frontend PID $FRONT_PID  http://127.0.0.1:5173"
trap 'kill $BACK_PID $FRONT_PID' INT TERM
wait
