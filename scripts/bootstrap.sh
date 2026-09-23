#!/usr/bin/env bash
# Развернуть каркас в репозиторий платформы: ./scripts/bootstrap.sh /path/to/platform-repo 5
set -euo pipefail
TARGET="$1"; TRACK="$2"
SRC="$(cd "$(dirname "$0")/.." && pwd)"
[ -d "$TARGET/.git" ] || { echo "$TARGET — не git-репозиторий"; exit 1; }
NN=$(printf "%02d" "$TRACK")
tar -C "$SRC" --exclude=.venv --exclude=venv --exclude=logs --exclude=__pycache__ \
    --exclude=.pytest_cache --exclude=.git --exclude=.env --exclude=wheels -cf - . | tar -C "$TARGET" -xf -
cp "$SRC/context/ideas/track-$NN.md" "$TARGET/docs/IDEA.md"
cp "$SRC/context/tracks/track-$NN.md" "$TARGET/docs/TRACK.md"
if [ -d "$SRC/context/samples/track-$NN" ]; then
  find "$SRC/context/samples/track-$NN" -maxdepth 1 -type f -exec cp {} "$TARGET/data/samples/" \;
  cp "$SRC/context/samples/track-$NN/eval/"*.json "$TARGET/eval/cases/" 2>/dev/null || true
fi
[ -f "$TARGET/docs/CASE.md" ] || printf '# Кейс организаторов (вставить дословно)\n' > "$TARGET/docs/CASE.md"
cd "$TARGET" && git add -A && git commit -m "chore: import pre-built harness (disclosed in docs/DISCLOSURE.md), track $TRACK"
echo "Готово. Вставить кейс в docs/CASE.md, затем /kickoff $TRACK (Claude) или codex 'Выполни prompts/00-kickoff.md'."
