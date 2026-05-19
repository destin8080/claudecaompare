#!/usr/bin/env bash
# ----------------------------------------------------------------------
# First-time setup. Installs Python deps, Playwright Chromium, npm deps.
# Run once after cloning the repo.
# ----------------------------------------------------------------------
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "▶ Compare Your Website — first-time setup"
echo

# Backend
cd "$ROOT/backend"
if [ ! -d ".venv" ]; then
  echo "▶ Creating Python virtualenv..."
  python3 -m venv .venv
fi
source .venv/bin/activate
echo "▶ Installing Python dependencies..."
pip install --quiet --disable-pip-version-check -r requirements.txt
echo "▶ Installing Playwright Chromium (downloads ~150 MB)..."
playwright install chromium

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "▶ Created backend/.env from example."
fi

# Frontend
cd "$ROOT/frontend"
echo "▶ Installing npm dependencies..."
npm install --silent --no-audit --no-fund
if [ ! -f ".env.local" ]; then
  cp .env.example .env.local
  echo "▶ Created frontend/.env.local from example."
fi

echo
echo "✓ Setup complete. Run ./start.sh to launch both services."
