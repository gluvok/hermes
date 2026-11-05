#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi
if [ -x "$DIR/bin/hermes" ]; then
    exec "$DIR/bin/hermes" "$@"
elif command -v uv >/dev/null 2>&1; then
    exec uv run python main.py "$@"
else
    exec python3 main.py "$@"
fi
