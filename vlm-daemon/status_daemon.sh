#!/bin/sh
set -eu

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SKILL_DIR/vlm_daemon.pid"
PYTHON="${PYTHON:-/usr/local/bin/python3}"
HOST="${VLM_DAEMON_HOST:-127.0.0.1}"
PORT="${VLM_DAEMON_PORT:-18080}"
CURL_BIN="${CURL_BIN:-/usr/bin/curl}"

status="stopped"
pid=""

if [ -f "$PID_FILE" ]; then
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        status="running"
    else
        status="stale_pid"
    fi
fi

api_ok="false"
api_status="unreachable"
model_loaded="false"
model_alias=""
model_loading="false"
loading_model_alias=""
autoload_ok=""

if [ "$status" = "running" ]; then
    health_json="$($CURL_BIN -s --max-time 2 "http://${HOST}:${PORT}/health" 2>/dev/null || true)"
    if [ -n "$health_json" ]; then
        api_ok="true"
        parsed="$($PYTHON - "$health_json" <<'PY'
import json
import sys

obj = json.loads(sys.argv[1])
api_status = obj.get("status", "unknown")
model = obj.get("model") or {}
loaded = bool(model.get("loaded", False))
alias = model.get("model_alias") or ""
loading = bool(model.get("loading", False))
loading_alias = model.get("loading_model_alias") or ""
autoload = obj.get("autoload") or {}
autoload_ok = autoload.get("ok", "")
print(api_status)
print("true" if loaded else "false")
print(alias)
print("true" if loading else "false")
print(loading_alias)
print("" if autoload_ok == "" else ("true" if bool(autoload_ok) else "false"))
PY
        )"
        api_status="$(printf '%s\n' "$parsed" | sed -n '1p')"
        model_loaded="$(printf '%s\n' "$parsed" | sed -n '2p')"
        model_alias="$(printf '%s\n' "$parsed" | sed -n '3p')"
    model_loading="$(printf '%s\n' "$parsed" | sed -n '4p')"
    loading_model_alias="$(printf '%s\n' "$parsed" | sed -n '5p')"
    autoload_ok="$(printf '%s\n' "$parsed" | sed -n '6p')"
    fi
fi

printf 'status=%s\n' "$status"
printf 'pid=%s\n' "${pid:-none}"
printf 'api_ok=%s\n' "$api_ok"
printf 'api_status=%s\n' "$api_status"
printf 'model_loaded=%s\n' "$model_loaded"
printf 'model_alias=%s\n' "${model_alias:-none}"
printf 'model_loading=%s\n' "$model_loading"
if [ "$model_loading" = "true" ] && [ -n "$loading_model_alias" ]; then
    printf 'loading_model_alias=%s\n' "$loading_model_alias"
fi
if [ -n "$autoload_ok" ]; then
    printf 'autoload_ok=%s\n' "$autoload_ok"
fi
