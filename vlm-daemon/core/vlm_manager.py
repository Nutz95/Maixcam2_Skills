import os
import time
import json
import gc
import subprocess
import urllib.request
import urllib.error
from threading import RLock
from typing import Dict, Optional

from maix import app as maix_app
from maix import err, image, nn
from maix import sys as maix_sys

from .model_catalog import ModelCatalog, VLMModelSpec


class VLMManager:
    """Loads, unloads, and queries a single active VLM instance."""

    def __init__(self, catalog: ModelCatalog) -> None:
        self._catalog = catalog
        self._lock = RLock()
        self._model_obj = None
        self._loaded_spec: Optional[VLMModelSpec] = None
        self._loaded_model_path: Optional[str] = None
        self._loading_alias: Optional[str] = None
        self._loading_started_at: Optional[int] = None
        # Monotonically-increasing counter — incremented by load_model (Phase 1) and
        # unload_model so that a concurrent or cancelled is_ready() wait can detect it
        # has been superseded and safely discard its model instance.
        self._load_generation: int = 0

    def _instantiate(self, spec: VLMModelSpec, model_path: str):
        cls = getattr(nn, spec.class_name, None)
        if cls is None:
            raise RuntimeError(f"maix.nn has no class '{spec.class_name}' for alias '{spec.alias}'")
        return cls(model_path)

    def _get_ready_timeout_seconds(self, alias: str) -> int:
        alias_key = (alias or "").strip().lower()
        # Keep this aligned with tests/test_vlmDaemon_menu.ps1 defaults.
        default_map = {
            "qwen3vl": 240,
            "internvl": 180,
            "smolvlm": 90,
        }
        default_timeout = default_map.get(alias_key, 180)

        global_env = os.environ.get("VLM_MODEL_READY_TIMEOUT")
        alias_env = os.environ.get(f"VLM_MODEL_READY_TIMEOUT_{alias_key.upper()}")
        raw = alias_env if alias_env else global_env
        if raw:
            try:
                parsed = int(raw)
                if parsed > 0:
                    return parsed
            except Exception:
                pass

        return default_timeout

    def _prepare_qwen3_runtime(self) -> None:
        # Mirror MaixPy app_vlm behavior for Qwen3-VL stability.
        try:
            mem_info = maix_sys.memory_info()
            hw_total = int(mem_info.get("hw_total", 0)) if isinstance(mem_info, dict) else 0
            if hw_total and hw_total < 4 * 1024 * 1024 * 1024:
                raise RuntimeError(
                    "Qwen3VL requires 4GB hardware. "
                    f"Detected hw_total={hw_total} bytes"
                )
        except RuntimeError:
            raise
        except Exception:
            # If memory introspection is unavailable, continue with best effort.
            pass

        try:
            ai_isp = maix_app.get_sys_config_kv("npu", "ai_isp", "1")
            if str(ai_isp) == "1":
                maix_app.set_sys_config_kv("npu", "ai_isp", "0")
        except Exception:
            # Non-fatal if unavailable on current runtime.
            pass

    def _stop_qwen3_service_if_running(self) -> None:
        # qwen3_vl system service can hold resources and interfere with other VLM models.
        try:
            subprocess.run(
                ["systemctl", "stop", "qwen3_vl.service"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=5,
            )
        except Exception:
            pass

    def _ask_qwen3_http(self, image_path: str, question: str) -> str:
        payload = {
            "model": "AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4",
            "stream": False,
            "temperature": 0.2,
            "repetition_penalty": 1,
            "top_p": 0.8,
            "top_k": 20,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {"type": "image_url", "image_url": image_path},
                    ],
                }
            ],
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url="http://127.0.0.1:12346/v1/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        parsed = json.loads(body)
        choices = parsed.get("choices") or []
        if not choices:
            return ""
        msg = choices[0].get("message") or {}
        content = msg.get("content") or ""
        return content.strip() if isinstance(content, str) else ""

    def _release_model_obj(self, model_obj, alias: Optional[str]) -> None:
        """Release model using SDK-defined lifecycle calls before dropping reference."""
        if model_obj is None:
            return

        # SDK API (maix.nn): cancel -> clear_image -> unload.
        # Qwen3VL additionally exposes stop_service().
        try:
            model_obj.cancel()
        except Exception:
            pass

        try:
            model_obj.clear_image()
        except Exception:
            pass

        try:
            model_obj.unload()
        except Exception:
            pass

        if alias == "qwen3vl":
            try:
                model_obj.stop_service()
            except Exception:
                pass

        try:
            del model_obj
        except Exception:
            pass

        if alias == "qwen3vl":
            self._stop_qwen3_service_if_running()

        # Promptly reclaim wrappers/FFI handles.
        try:
            gc.collect()
        except Exception:
            pass

    def load_model(self, alias: str, model_path: Optional[str] = None, system_prompt: Optional[str] = None) -> Dict:
        # ── Phase 1: validate path, unload old model, stamp generation. ──────────────────────
        # Lock held only for this fast section (< 0.1 s). No slow work here.
        with self._lock:
            spec = self._catalog.get(alias)
            resolved_path = self._catalog.find_model_path(spec, explicit_path=model_path)
            if not resolved_path:
                installed = self._catalog.list_installed_model_files()
                installed_msg = "\n".join(installed) if installed else "(none found)"
                requested = model_path or spec.default_model_path
                raise FileNotFoundError(
                    "Model file not found for alias "
                    f"'{alias}'. Requested path: {requested}.\n"
                    "You can pass --model-path to load a custom file.\n"
                    f"Installed model.mud files:\n{installed_msg}"
                )

            self.unload_model()  # clears _model_obj and bumps generation
            self._load_generation += 1
            my_generation = self._load_generation
            self._loading_alias = spec.alias
            self._loading_started_at = int(time.time())

        # ── Phase 2: prepare runtime + instantiate (slow, NO lock). ─────────────────────────
        # nn.Qwen3VL / nn.InternVL / nn.SmolVLM constructors start background services and
        # can block for up to ~60 s. Running without the lock keeps /health and other
        # endpoints fully responsive during load.
        # NOTE: is_ready() is intentionally NOT called here. For Qwen3VL, is_ready()
        # checks whether image processing is complete (must be called after set_image()),
        # not whether the service is initialised. For other models the constructor is
        # synchronous, so is_ready() after construction is unnecessary.
        try:
            if spec.alias == "qwen3vl":
                self._prepare_qwen3_runtime()
            else:
                self._stop_qwen3_service_if_running()

            model_obj = self._instantiate(spec, resolved_path)

            if system_prompt:
                model_obj.set_system_prompt(system_prompt)
            elif spec.alias == "qwen3vl":
                model_obj.set_system_prompt("You are Qwen3VL. You are a helpful vision-to-text assistant.")
        except Exception as e:
            with self._lock:
                if self._load_generation == my_generation:
                    self._loading_alias = None
                    self._loading_started_at = None
            raise RuntimeError(
                "Model instantiation failed for alias "
                f"'{spec.alias}' at path '{resolved_path}'. "
                "Verify model files are complete and hardware/resources match requirements. "
                f"Original error: {e}"
            ) from e

        # ── Phase 3: commit under lock, or discard if superseded. ───────────────────────────
        with self._lock:
            if self._load_generation != my_generation:
                # A concurrent unload() or newer load_model() ran while we were in Phase 2.
                # Discard our instance — the newer operation has already committed its state.
                self._release_model_obj(model_obj, spec.alias)
                return self.status()

            self._model_obj = model_obj
            self._loaded_spec = spec
            self._loaded_model_path = resolved_path
            self._loading_alias = None
            self._loading_started_at = None

        return self.status()

    def unload_model(self) -> Dict:
        model_obj = None
        loaded_alias: Optional[str] = None
        with self._lock:
            # Bump generation so any in-flight Phase-2 is_ready() wait discards its result.
            self._load_generation += 1
            self._loading_alias = None
            self._loading_started_at = None
            if self._model_obj is not None:
                model_obj = self._model_obj
                loaded_alias = self._loaded_spec.alias if self._loaded_spec else None
                self._model_obj = None
                self._loaded_spec = None
                self._loaded_model_path = None

            status = self.status()

        # Release outside lock to keep /health responsive during teardown.
        self._release_model_obj(model_obj, loaded_alias)
        return status

    def status(self) -> Dict:
        # Use a regular blocking acquire so /health is always responsive.
        # Phase 2 of load_model() does NOT hold the lock, so this never waits long.
        with self._lock:
            if self._loading_alias:
                return {
                    "loaded": False,
                    "model_alias": None,
                    "model_class": None,
                    "model_path": None,
                    "loading": True,
                    "loading_model_alias": self._loading_alias,
                    "loading_started_at": self._loading_started_at,
                }
            if not self._model_obj or not self._loaded_spec:
                return {
                    "loaded": False,
                    "model_alias": None,
                    "model_class": None,
                    "model_path": None,
                    "loading": False,
                }
            return {
                "loaded": True,
                "model_alias": self._loaded_spec.alias,
                "model_class": self._loaded_spec.class_name,
                "model_path": self._loaded_model_path,
                "loading": False,
            }

    def ask(self, image_path: str, question: str, fit_mode=image.Fit.FIT_CONTAIN) -> Dict:
        with self._lock:
            if not self._model_obj or not self._loaded_spec:
                raise RuntimeError("No model loaded. Call /models/load first.")
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")

            in_fmt = self._model_obj.input_format()
            img = image.load(image_path, format=in_fmt)
            # RGB888 input is capped at 1920x1080 by the NPU backend.
            if img.width() > 1920 or img.height() > 1080:
                img = img.resize(1920, 1080, image.Fit.FIT_CONTAIN)
            self._model_obj.set_image(img, fit=fit_mode)

            chunks = []
            used_backend = "sdk"

            # For qwen3vl, prefer local OpenAI-compatible backend first.
            if self._loaded_spec.alias == "qwen3vl":
                try:
                    http_answer = self._ask_qwen3_http(image_path=image_path, question=question)
                    if http_answer:
                        return {
                            "model": self._loaded_spec.alias,
                            "image_path": image_path,
                            "question": question,
                            "answer": http_answer,
                            "backend": "http_primary",
                        }
                except Exception:
                    # Fall back to SDK path below.
                    pass

            def on_reply(_obj, resp):
                chunk = getattr(resp, "msg_new", "")
                if chunk:
                    chunks.append(chunk)

            self._model_obj.set_reply_callback(on_reply)
            sdk_error: Optional[Exception] = None
            resp = None
            try:
                resp = self._model_obj.send(question)
                err.check_raise(resp.err_code)
            except Exception as e:
                sdk_error = e

            # Different Maix model classes expose output text with different field names.
            answer = ""
            if resp is not None:
                for attr in ("msg", "answer", "text", "content"):
                    value = getattr(resp, attr, "")
                    if isinstance(value, str) and value.strip():
                        answer = value.strip()
                        break

            if not answer:
                answer = "".join(chunks).strip()

            # qwen3vl has a reliable OpenAI-compatible local backend; use it as fallback.
            if self._loaded_spec.alias == "qwen3vl" and (not answer):
                try:
                    http_answer = self._ask_qwen3_http(image_path=image_path, question=question)
                    if http_answer:
                        answer = http_answer
                        used_backend = "http_fallback"
                except Exception:
                    # Keep original behavior if fallback also fails.
                    pass

            if not answer and sdk_error is not None:
                raise RuntimeError(f"SDK ask failed and fallback returned empty answer: {sdk_error}") from sdk_error

            if not answer:
                # Keep API contract stable, but return a meaningful diagnostic string.
                answer = "[empty model response]"

            return {
                "model": self._loaded_spec.alias,
                "image_path": image_path,
                "question": question,
                "answer": answer,
                "backend": used_backend,
            }
