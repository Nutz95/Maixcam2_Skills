#!/usr/bin/env python3
"""Native Python control helpers for the VLM daemon."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Dict, List, Optional

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SKILL_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from python_tools.maix_env import ensure_maix_env

ensure_maix_env()

PID_FILE = os.path.join(SKILL_DIR, "vlm_daemon.pid")
LOG_FILE = os.path.join(SKILL_DIR, "logs", "vlm_daemon.log")
DAEMON_FILE = os.path.join(SKILL_DIR, "daemon_api.py")
HOST = os.environ.get("VLM_DAEMON_HOST", "127.0.0.1")
PORT = int(os.environ.get("VLM_DAEMON_PORT", "18080"))
PYTHON = os.environ.get("PYTHON", sys.executable or "/usr/local/bin/python3")


def http_json(method: str, url: str, payload=None, timeout: int = 180) -> Dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url=url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error: {e.reason}") from e


def _read_pid_file() -> Optional[int]:
    if not os.path.exists(PID_FILE):
        return None
    try:
        raw = open(PID_FILE, "r", encoding="utf-8").read().strip()
    except OSError:
        return None
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _pid_alive(pid: Optional[int]) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _find_orphan_pids() -> List[int]:
    cmd = ["pgrep", "-f", "/vlm-daemon/daemon_api.py"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError:
        return []

    if result.returncode not in (0, 1):
        return []

    pids: List[int] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pid = int(line)
        except ValueError:
            continue
        if pid != os.getpid():
            pids.append(pid)
    return pids


def _kill_pid(pid: int) -> None:
    if not _pid_alive(pid):
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return
    for _ in range(5):
        if not _pid_alive(pid):
            return
        time.sleep(1)
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass


def stop_daemon(quiet: bool = False) -> int:
    pid = _read_pid_file()
    orphans = _find_orphan_pids()

    if pid is None and not os.path.exists(PID_FILE):
        if orphans:
            for orphan in orphans:
                _kill_pid(orphan)
            if not quiet:
                print(f"Stopped orphan daemon process(es): {' '.join(str(p) for p in orphans)}")
        elif not quiet:
            print("Daemon not running (no pid file).")
        return 0

    if pid is None:
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
        if not quiet:
            print("Daemon pid file was empty, cleaned.")
        if orphans:
            for orphan in orphans:
                _kill_pid(orphan)
            if not quiet:
                print(f"Stopped orphan daemon process(es): {' '.join(str(p) for p in orphans)}")
        return 0

    _kill_pid(pid)

    extras: List[int] = []
    for orphan in orphans:
        if orphan != pid:
            _kill_pid(orphan)
            extras.append(orphan)

    try:
        os.remove(PID_FILE)
    except OSError:
        pass

    if not quiet:
        if extras:
            print(f"Stopped daemon pid={pid} and extra process(es): {' '.join(str(p) for p in extras)}")
        else:
            print(f"Stopped daemon pid={pid}")
    return 0


def start_daemon() -> int:
    os.makedirs(os.path.join(SKILL_DIR, "logs"), exist_ok=True)

    pid = _read_pid_file()
    if _pid_alive(pid):
        print(f"Daemon already running (pid={pid})")
        return 0

    stop_daemon(quiet=True)

    with open(LOG_FILE, "a", encoding="utf-8") as log_fp:
        proc = subprocess.Popen(
            [PYTHON, DAEMON_FILE],
            cwd=SKILL_DIR,
            stdout=log_fp,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=os.environ.copy(),
        )

    with open(PID_FILE, "w", encoding="utf-8") as fp:
        fp.write(str(proc.pid))

    print(f"VLM daemon started on {HOST}:{PORT} (pid={proc.pid})")
    print(f"Logs: {LOG_FILE}")
    return 0


def status_dict() -> Dict[str, str]:
    status = "stopped"
    pid = _read_pid_file()
    if os.path.exists(PID_FILE):
        if _pid_alive(pid):
            status = "running"
        else:
            status = "stale_pid"

    data = {
        "status": status,
        "pid": str(pid) if pid else "none",
        "api_ok": "false",
        "api_status": "unreachable",
        "model_loaded": "false",
        "model_alias": "none",
        "model_loading": "false",
    }

    if status != "running":
        return data

    try:
        health = http_json("GET", f"http://{HOST}:{PORT}/health", timeout=2)
    except Exception:
        return data

    data["api_ok"] = "true"
    data["api_status"] = str(health.get("status", "unknown"))

    model = health.get("model") or {}
    if model.get("loaded"):
        data["model_loaded"] = "true"
    if model.get("model_alias"):
        data["model_alias"] = str(model.get("model_alias"))
    if model.get("loading"):
        data["model_loading"] = "true"
    if model.get("loading_model_alias"):
        data["loading_model_alias"] = str(model.get("loading_model_alias"))

    autoload = health.get("autoload") or {}
    if "ok" in autoload:
        data["autoload_ok"] = "true" if bool(autoload.get("ok")) else "false"
    return data


def print_status() -> int:
    data = status_dict()
    print(f"status={data['status']}")
    print(f"pid={data['pid']}")
    print(f"api_ok={data['api_ok']}")
    print(f"api_status={data['api_status']}")
    print(f"model_loaded={data['model_loaded']}")
    print(f"model_alias={data['model_alias']}")
    print(f"model_loading={data['model_loading']}")
    if data.get("loading_model_alias"):
        print(f"loading_model_alias={data['loading_model_alias']}")
    if "autoload_ok" in data:
        print(f"autoload_ok={data['autoload_ok']}")
    return 0