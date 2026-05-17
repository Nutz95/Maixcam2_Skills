import os
import time
import gc
from typing import Optional

from maix import camera


class CameraService:
    """Handles camera lifecycle and 2K captures (singleton pattern)."""

    def __init__(self, output_dir: str = "/root/.picoclaw/workspace/vlm_captures") -> None:
        self._output_dir = output_dir
        self._cam = None
        self._init_camera()

    def _cleanup_capture_dir(self) -> None:
        """Keep only the next capture in the managed capture directory."""
        os.makedirs(self._output_dir, exist_ok=True)
        for name in os.listdir(self._output_dir):
            path = os.path.join(self._output_dir, name)
            if not os.path.isfile(path):
                continue
            lower = name.lower()
            if lower.endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp")):
                try:
                    os.remove(path)
                except OSError:
                    pass

    def _init_camera(self):
        from maix import camera
        if self._cam is not None:
            return
        self._cam = camera.Camera()
        self._cam.set_resolution(width=2160, height=1440)
        self._cam.skip_frames(30)

    def close(self):
        # SDK contract for maix.camera.Camera: use is_opened()/close().
        cam = self._cam
        self._cam = None
        if cam is None:
            return

        try:
            is_opened = getattr(cam, "is_opened", None)
            if callable(is_opened):
                if is_opened():
                    cam.close()
            else:
                cam.close()
        except Exception:
            pass

        try:
            del cam
        except Exception:
            pass

        try:
            gc.collect()
        except Exception:
            pass

    def capture_2k(self, output_path: Optional[str] = None) -> str:
        self._cleanup_capture_dir()
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
