#!/bin/sh
set -eu

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-/usr/local/bin/python3}"

HOST="${VLM_DAEMON_HOST:-127.0.0.1}"
PORT="${VLM_DAEMON_PORT:-18080}"

usage() {
    cat <<'EOF'
Usage:
  ./vlmctl.sh start
  ./vlmctl.sh stop
  ./vlmctl.sh status
  ./vlmctl.sh models
  ./vlmctl.sh load <qwen3vl|internvl|smolvlm>
  ./vlmctl.sh unload
  ./vlmctl.sh capture [output_path]
  ./vlmctl.sh ask <question>
  ./vlmctl.sh ask-image <image_path> <question>

Notes:
  - ask uses capture_new=true
  - ask-image uses capture_new=false
EOF
}

api() {
    "$PYTHON" "$SKILL_DIR/api_client.py" --host "$HOST" --port "$PORT" "$@"
}

if [ "$#" -lt 1 ]; then
    usage
    exit 2
fi

case "$1" in
    start)
        "$SKILL_DIR/start_daemon.sh"
        ;;
    stop)
        "$SKILL_DIR/stop_daemon.sh"
        ;;
    status)
        "$SKILL_DIR/status_daemon.sh"
        ;;
    models)
        api --pretty models
        ;;
    load)
        if [ "$#" -lt 2 ]; then
            echo "Missing model alias"
            usage
            exit 2
        fi
        api --pretty load --model "$2"
        ;;
    unload)
        api --pretty unload
        ;;
    capture)
        if [ "$#" -ge 2 ]; then
            api --pretty capture --output-path "$2"
        else
            api --pretty capture
        fi
        ;;
    ask)
        if [ "$#" -lt 2 ]; then
            echo "Missing question"
            usage
            exit 2
        fi
        question="$2"
        shift 2
        # Support questions with spaces when passed without quotes by joining leftovers.
        if [ "$#" -gt 0 ]; then
            for part in "$@"; do
                question="$question $part"
            done
        fi
        api --pretty ask --question "$question" --capture-new
        ;;
    ask-image)
        if [ "$#" -lt 3 ]; then
            echo "Missing image_path or question"
            usage
            exit 2
        fi
        image_path="$2"
        question="$3"
        shift 3
        if [ "$#" -gt 0 ]; then
            for part in "$@"; do
                question="$question $part"
            done
        fi
        api --pretty ask --question "$question" --image-path "$image_path"
        ;;
    *)
        usage
        exit 2
        ;;
esac
