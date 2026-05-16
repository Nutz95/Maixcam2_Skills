#!/usr/bin/env python3
"""Skill photo-2k : Prise de photo en 2K avec MaixPy

✅ Fonctionne dans l'environnement MaixCAM2 !
"""

import sys
import os
import time
import json
import urllib.error
import urllib.request

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SKILL_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from python_tools.maix_env import ensure_maix_env
from python_tools.picoclaw_notify import notify_image

ensure_maix_env()

from maix import camera, image, nn


VLM_BASE_URL = os.environ.get("VLM_DAEMON_URL", "http://127.0.0.1:18080")


def _vlm_daemon_is_running(base_url=VLM_BASE_URL, timeout=1.5):
    """Return True when the local VLM daemon responds on /health."""
    try:
        with urllib.request.urlopen(base_url + "/health", timeout=timeout) as resp:
            if resp.status != 200:
                return False
            payload = json.loads(resp.read().decode("utf-8"))
            return bool(payload.get("ok"))
    except Exception:
        return False


def _capture_via_vlm_daemon(path_output, base_url=VLM_BASE_URL, timeout=8):
    """Ask the daemon camera singleton to capture and return parsed JSON or None."""
    payload = {"output_path": path_output}
    req = urllib.request.Request(
        base_url + "/capture",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None

def capture_photo(path_output="/root/.picoclaw/workspace/capture_photo_2k.jpg"):
    """Capture une photo 2K avec la caméra Maix"""
    
    try:
        # If daemon is alive, use its camera singleton to avoid camera lock conflicts.
        if _vlm_daemon_is_running():
            daemon_result = _capture_via_vlm_daemon(path_output)
            if daemon_result and str(daemon_result.get("ok", "")).lower() != "false":
                image_path = daemon_result.get("image_path") or path_output
                print("[INFO] Capture réalisée via API daemon VLM")
                print(f"[INFO] Fichier : {image_path}")

                picoclaw_sent = notify_image(image_path, f"2K image captured: {image_path}")
                if picoclaw_sent:
                    print("[PICOCLAW] Notification sent via picoclaw library")
                else:
                    print("[PICOCLAW] Library not available or no compatible helper found")

                summary = {
                    "image_file": image_path,
                    "resolution": "2160x1440",
                    "quality": 95,
                    "send_policy": "image_only",
                    "capture_mode": "vlm_daemon_api",
                    "picoclaw_notified": picoclaw_sent,
                }
                print(f"IMAGE_FILE: {image_path}")
                print("SEND_POLICY: image_only")
                print("PICOCLAW_RESULT_JSON=" + json.dumps(summary, ensure_ascii=False))
                return True

            print("[WARN] Daemon actif mais capture API échouée, fallback capture locale")

        # Initialiser la caméra
        cam = camera.Camera()
        
        # Définir la résolution 2K
        cam.set_resolution(width=2160, height=1440)
        
        # Skipper 30 images pour stabilisation
        cam.skip_frames(30)
        
        # Récupérer une image
        img = cam.read()
        
        # Sauvegarder l'image avec qualité 95%
        img.save(path=path_output, quality=95)
        
        print(f"✅ Photo 2K capturée avec succès !")
        print(f"📁 Fichier : {path_output}")
        print(f"📏 Résolution : 2160x1440")
        print(f"🎨 Qualité : 95%")

        picoclaw_sent = notify_image(path_output, f"2K image captured: {path_output}")
        if picoclaw_sent:
            print("[PICOCLAW] Notification sent via picoclaw library")
        else:
            print("[PICOCLAW] Library not available or no compatible helper found")

        summary = {
            "image_file": path_output,
            "resolution": "2160x1440",
            "quality": 95,
            "send_policy": "image_only",
            "capture_mode": "direct_camera",
            "picoclaw_notified": picoclaw_sent,
        }
        print(f"IMAGE_FILE: {path_output}")
        print("SEND_POLICY: image_only")
        print("PICOCLAW_RESULT_JSON=" + json.dumps(summary, ensure_ascii=False))
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la capture : {e}")
        print("⚠️  Vérifiez que la caméra Maix est connectée et les drivers installés")
        return False

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "/root/.picoclaw/workspace/capture_photo_2k.jpg"
    capture_photo(path)