from typing import Dict, Optional

from .camera_service import CameraService
from .model_catalog import ModelCatalog
from .vlm_manager import VLMManager


class VLMApiService:
    """Application service used by Flask routes."""

    def __init__(self, catalog: ModelCatalog, vlm_manager: VLMManager, camera_service: CameraService) -> None:
        self._catalog = catalog
        self._vlm_manager = vlm_manager
        self._camera_service = camera_service

    def list_models(self):
        models = []
        installed_files = self._catalog.list_installed_model_files()
        for spec in self._catalog.list_models():
            resolved = self._catalog.find_model_path(spec)
            models.append(
                {
                    "alias": spec.alias,
                    "class_name": spec.class_name,
                    "default_model_path": spec.default_model_path,
                    "description": spec.description,
                    "available": bool(resolved),
                    "resolved_model_path": resolved,
                }
            )
        return {
            "supported": models,
            "installed_model_files": installed_files,
        }

    def load_model(self, alias: str, model_path: Optional[str], system_prompt: Optional[str]) -> Dict:
        return self._vlm_manager.load_model(alias=alias, model_path=model_path, system_prompt=system_prompt)

    def unload_model(self) -> Dict:
        return self._vlm_manager.unload_model()

    def shutdown(self) -> Dict:
        model_status = self._vlm_manager.unload_model()
        self._camera_service.close()
        return {
            "model": model_status,
            "camera_closed": True,
        }

    def status(self) -> Dict:
        return self._vlm_manager.status()

    def capture_only(self, output_path: Optional[str]) -> Dict:
        image_path = self._camera_service.capture_2k(output_path=output_path)
        return {
            "image_path": image_path,
            "send_policy": "image_only",
        }

    def capture_and_ask(self, question: str, output_path: Optional[str]) -> Dict:
        image_path = self._camera_service.capture_2k(output_path=output_path)
        result = self._vlm_manager.ask(image_path=image_path, question=question)
        result["send_policy"] = "report_and_image"
        return result

    def ask_on_existing_image(self, question: str, image_path: str) -> Dict:
        result = self._vlm_manager.ask(image_path=image_path, question=question)
        result["send_policy"] = "report_only"
        return result
