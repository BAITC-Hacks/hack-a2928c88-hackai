#!/usr/bin/env bash
# Локальный запуск (Git Bash / Linux / macOS): ./scripts/dev.sh
set -euo pipefail
[ -d .venv ] || python -m venv .venv
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate
pip install -q -r requirements.txt
[ -f .env ] && set -a && . ./.env && set +a
uvicorn app.main:app --reload --port 8000
