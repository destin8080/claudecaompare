#!/usr/bin/env bash
# ----------------------------------------------------------------------
# One-shot launcher for Compare Your Website (backend + frontend).
# ----------------------------------------------------------------------
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

echo "▶ Compare Your Website — starting both services"
echo "   project root: $ROOT"
echo

# ---------- backend ----------
if [ ! -d "$BACKEND/.venv" ]; then
  echo "✗ backend/.venv not found."
  echo "  Run setup first: cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && playwright install chromium"
  exit 1
fi

if [ ! -f "$BACKEND/.env" ]; then
  echo "ℹ  backend/.env not found — copying from .env.example (Stripe disabled until you fill it in)."
  cp "$BACKEND/.env.example" "$BACKEND/.env"
fi

if [ ! -d "$FRONTEND/node_modules" ]; then
  echo "✗ frontend/node_modules not found."
  echo "  Run setup first: cd frontend && npm install"
  exit 1
fi

if [ ! -f "$FRONTEND/.env.local" ]; then
  cp "$FRONTEND/.env.example" "$FRONTEND/.env.local"
fi

# Boot backend
cd "$BACKEND"
source .venv/bin/activate
echo "▶ Backend  : http://localhost:8000"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Boot frontend
cd "$FRONTEND"
echo "▶ Frontend : http://localhost:3000"
npm run dev &
FRONTEND_PID=$!

trap "echo; echo '▼ Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

echo
echo "Open http://localhost:3000 in your browser. Press Ctrl-C to stop both."
wait
