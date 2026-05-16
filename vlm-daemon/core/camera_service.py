import os
import time
from typing import Optional

from maix import camera


class CameraService:
    """Handles camera lifecycle and 2K captures."""

    def __init__(self, output_dir: str = "/root/.picoclaw/workspace") -> None:
        self._output_dir = output_dir
        self._cam = None

    def __del__(self) -> None:
        if self._cam is not None:
            del self._cam

    def _ensure_cam(self) -> None:
        # kept for compatibility; prefer per-capture camera creation
        return

    def capture_2k(self, output_path: Optional[str] = None) -> str:
        os.makedirs(self._output_dir, exist_ok=True)
        if not output_path:
            ts = time.strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self._output_dir, f"vlm_capture_{ts}_2k.jpg")

        # Create and destroy a camera instance for each capture. This avoids
        # repeated VI driver re-init issues when the daemon handles multiple
        # consecutive captures/asks.
        cam = camera.Camera()
        try:
            cam.set_resolution(width=2160, height=1440)
            cam.skip_frames(30)
            img = cam.read()
            img.save(path=output_path, quality=95)
        finally:
            try:
                del cam
            except Exception:
                pass

        return output_path
