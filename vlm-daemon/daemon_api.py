#!/usr/bin/env python3
"""Flask daemon exposing VLM + capture APIs on MaixCAM2."""

import os
import sys
import threading
import time
from typing import Any, Dict

from flask import Flask, jsonify, request

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SKILL_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from python_tools.maix_env import ensure_maix_env

ensure_maix_env()

from core.api_service import VLMApiService
from core.camera_service import CameraService
from core.model_catalog import ModelCatalog
from core.vlm_manager import VLMManager


def _ok(payload: Dict[str, Any], status: int = 200):
    return jsonify({"ok": True, **payload}), status


def _err(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status


def create_app() -> Flask:
    app = Flask(__name__)

    catalog = ModelCatalog()
    vlm_manager = VLMManager(catalog)
    camera_service = CameraService(output_dir="/root/.picoclaw/workspace")
    svc = VLMApiService(catalog, vlm_manager, camera_service)

    auto_model = os.environ.get("VLM_AUTOLOAD_MODEL", "qwen3vl").strip().lower()
    autoload_result: Dict[str, Any] = {
        "enabled": bool(auto_model),
        "model": auto_model,
        "ok": False,
        "state": "disabled" if not auto_model else "pending",
    }
    autoload_lock = threading.Lock()

    def _set_autoload(update: Dict[str, Any]) -> None:
        with autoload_lock:
            autoload_result.update(update)

    def _run_autoload() -> None:
        if not auto_model:
            return

        _set_autoload({"state": "in_progress", "started_at": int(time.time())})
        try:
            model_status = svc.load_model(alias=auto_model, model_path=None, system_prompt=None)
            _set_autoload({
                "ok": True,
                "state": "done",
                "status": model_status,
                "finished_at": int(time.time()),
            })
            app.logger.info("Autoloaded model '%s'", auto_model)
        except Exception as e:
            _set_autoload({
                "ok": False,
                "state": "failed",
                "error": str(e),
                "finished_at": int(time.time()),
            })
            app.logger.warning("Autoload model '%s' failed: %s", auto_model, e)

    @app.get("/health")
    def health():
        with autoload_lock:
            autoload_snapshot = dict(autoload_result)
        return _ok({"status": "running", "model": svc.status(), "autoload": autoload_snapshot})

    @app.get("/models")
    def list_models():
        return _ok({"models": svc.list_models(), "current": svc.status()})

    @app.post("/models/load")
    def load_model():
        data = request.get_json(silent=True) or {}
        alias = data.get("model")
        if not alias:
            return _err("Missing required field: model")
        model_path = data.get("model_path")
        system_prompt = data.get("system_prompt")
        try:
            status = svc.load_model(alias=alias, model_path=model_path, system_prompt=system_prompt)
            return _ok({"message": "model_loaded", "model": status})
        except Exception as e:
            return _err(str(e))

    @app.post("/models/unload")
    def unload_model():
        status = svc.unload_model()
        return _ok({"message": "model_unloaded", "model": status})

    @app.post("/capture")
    def capture_only():
        data = request.get_json(silent=True) or {}
        output_path = data.get("output_path")
        try:
            result = svc.capture_only(output_path=output_path)
            return _ok(result)
        except Exception as e:
            return _err(str(e))

    @app.post("/ask")
    def ask():
        data = request.get_json(silent=True) or {}
        question = data.get("question")
        if not question:
            return _err("Missing required field: question")

        capture_new = bool(data.get("capture_new", True))
        output_path = data.get("output_path")
        image_path = data.get("image_path")

        try:
            if capture_new:
                result = svc.capture_and_ask(question=question, output_path=output_path)
            else:
                if not image_path:
                    return _err("When capture_new=false, image_path is required")
                result = svc.ask_on_existing_image(question=question, image_path=image_path)
            return _ok(result)
        except Exception as e:
            return _err(str(e))

    if auto_model:
        threading.Thread(target=_run_autoload, daemon=True).start()

    return app


if __name__ == "__main__":
    host = os.environ.get("VLM_DAEMON_HOST", "127.0.0.1")
    port = int(os.environ.get("VLM_DAEMON_PORT", "18080"))
    app = create_app()
    app.run(host=host, port=port, debug=False, threaded=True)
