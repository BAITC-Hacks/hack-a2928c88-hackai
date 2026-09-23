#!/usr/bin/env bash
# Почасовой чекпоинт (п. 6.6): ./scripts/checkpoint.sh 2 "основной сценарий работает end-to-end"
set -uo pipefail
HOUR="$1"; NOTE="$2"; TS="$(date +%H:%M)"
printf '\n## Час %s — %s\n- %s\n- Коммит: (см. git log, тег hour-%s)\n' "$HOUR" "$TS" "$NOTE" "$HOUR" >> docs/PROGRESS.md
python -m pytest -q || echo "WARN: тесты падают — чинить в следующем часу"
git add -A
git commit -m "checkpoint(hour-$HOUR): $NOTE"
git tag -f "hour-$HOUR"
git push && git push -f origin "hour-$HOUR"
echo "Чекпоинт часа $HOUR отправлен."
