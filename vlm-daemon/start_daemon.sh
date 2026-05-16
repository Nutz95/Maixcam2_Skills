#!/bin/sh
set -eu

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SKILL_DIR/vlm_daemon.pid"
LOG_FILE="$SKILL_DIR/logs/vlm_daemon.log"
HOST="${VLM_DAEMON_HOST:-127.0.0.1}"
PORT="${VLM_DAEMON_PORT:-18080}"

mkdir -p "$SKILL_DIR/logs"

if [ -f "$PID_FILE" ]; then
    PID="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        echo "Daemon already running (pid=$PID)"
        exit 0
    fi
fi

# Clean stale pid and potential orphan daemon_api.py processes before start.
"$SKILL_DIR/stop_daemon.sh" >/dev/null 2>&1 || true

cd "$SKILL_DIR"
nohup /usr/local/bin/python3 daemon_api.py >> "$LOG_FILE" 2>&1 &
PID="$!"
echo "$PID" > "$PID_FILE"

echo "VLM daemon started on $HOST:$PORT (pid=$PID)"
echo "Logs: $LOG_FILE"
