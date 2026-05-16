import os
import time
from typing import Optional

from maix import camera


class CameraService:
    """Handles camera lifecycle and 2K captures (singleton pattern)."""

    def __init__(self, output_dir: str = "/root/.picoclaw/workspace") -> None:
        self._output_dir = output_dir
        self._cam = None
        self._init_camera()

    def _init_camera(self):
        from maix import camera
        if self._cam is not None:
            return
        self._cam = camera.Camera()
        self._cam.set_resolution(width=2160, height=1440)
        self._cam.skip_frames(30)

    def close(self):
        # Libère la caméra proprement à l'arrêt du daemon
        if self._cam is not None:
            try:
                # S'il existe une méthode close(), l'utiliser
                if hasattr(self._cam, "close"):
                    self._cam.close()
            except Exception:
                pass
            self._cam = None

    def capture_2k(self, output_path: Optional[str] = None) -> str:
        os.makedirs(self._output_dir, exist_ok=True)
        if not output_path:
            ts = time.strftime("%Y%m%d_%H%M%S")
            ms = int((time.time() % 1) * 1000)
            output_path = os.path.join(self._output_dir, f"vlm_capture_{ts}_{ms:03d}_2k.jpg")

        # Utilise l'instance unique de caméra
        if self._cam is None:
            self._init_camera()
        cam = self._cam
        img = cam.read()
        img.save(path=output_path, quality=95)
        return output_path
