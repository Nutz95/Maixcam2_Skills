#!/bin/sh
set -eu

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-/usr/local/bin/python3}"

exec "$PYTHON" "$SKILL_DIR/status_daemon.py" "$@"
