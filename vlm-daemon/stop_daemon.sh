#!/bin/sh
set -eu

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SKILL_DIR/vlm_daemon.pid"

kill_pid() {
    target_pid="$1"
    if [ -z "$target_pid" ]; then
        return
    fi
    if kill -0 "$target_pid" 2>/dev/null; then
        kill "$target_pid" 2>/dev/null || true
        for _ in 1 2 3 4 5; do
            if ! kill -0 "$target_pid" 2>/dev/null; then
                return
            fi
            sleep 1
        done
        kill -9 "$target_pid" 2>/dev/null || true
    fi
}

ORPHANS="$(pgrep -f '/vlm-daemon/daemon_api.py' 2>/dev/null || true)"

if [ ! -f "$PID_FILE" ]; then
    if [ -n "$ORPHANS" ]; then
        for p in $ORPHANS; do
            kill_pid "$p"
        done
        echo "Stopped orphan daemon process(es): $ORPHANS"
    else
        echo "Daemon not running (no pid file)."
    fi
    exit 0
fi

PID="$(cat "$PID_FILE" 2>/dev/null || true)"
if [ -z "$PID" ]; then
    rm -f "$PID_FILE"
    echo "Daemon pid file was empty, cleaned."
    if [ -n "$ORPHANS" ]; then
        for p in $ORPHANS; do
            kill_pid "$p"
        done
        echo "Stopped orphan daemon process(es): $ORPHANS"
    fi
    exit 0
fi

kill_pid "$PID"

remaining=""
for p in $ORPHANS; do
    if [ "$p" != "$PID" ]; then
        kill_pid "$p"
        remaining="$remaining $p"
    fi
done

if [ -n "$remaining" ]; then
    echo "Stopped daemon pid=$PID and extra process(es):$remaining"
else
    echo "Stopped daemon pid=$PID"
fi

rm -f "$PID_FILE"
