import os
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class VLMModelSpec:
    alias: str
    class_name: str
    default_model_path: str
    description: str
    required_tokens: List[str]
    optional_tokens: List[str]


class ModelCatalog:
    """Single source of truth for supported VLM models on MaixCAM2."""

    def __init__(self) -> None:
        self._models: Dict[str, VLMModelSpec] = {
            "smolvlm": VLMModelSpec(
                alias="smolvlm",
                class_name="SmolVLM",
                default_model_path="/root/models/smolvlm-256m-instruct-maixcam2/model.mud",
                description="SmolVLM 256M instruct model",
                required_tokens=["smolvlm"],
                optional_tokens=[],
            ),
            "qwen3vl": VLMModelSpec(
                alias="qwen3vl",
                class_name="Qwen3VL",
                default_model_path="/root/models/Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448-maixcam2/model.mud",
                description="Qwen3-VL 2B Int4 model",
                required_tokens=["qwen3"],
                optional_tokens=["vl"],
            ),
            "internvl": VLMModelSpec(
                alias="internvl",
                class_name="InternVL",
                default_model_path="/root/models/InternVL2.5-1B-maixcam2/model.mud",
                description="InternVL2.5 1B model",
                required_tokens=["internvl"],
                optional_tokens=[],
            ),
        }

    def list_models(self) -> List[VLMModelSpec]:
        return [self._models[k] for k in sorted(self._models.keys())]

    def get(self, alias: str) -> VLMModelSpec:
        key = (alias or "").strip().lower()
        if key not in self._models:
            allowed = ", ".join(sorted(self._models.keys()))
            raise ValueError(f"Unsupported model '{alias}'. Supported models: {allowed}")
        return self._models[key]

    def find_model_path(self, spec: VLMModelSpec, explicit_path: Optional[str] = None) -> Optional[str]:
        if explicit_path:
            return explicit_path if os.path.exists(explicit_path) else None

        if os.path.exists(spec.default_model_path):
            return spec.default_model_path

        roots = ["/root/models", "/maixapp/share/models"]
        required = [t.lower() for t in spec.required_tokens]
        optional = [t.lower() for t in spec.optional_tokens]

        for root in roots:
            if not os.path.isdir(root):
                continue
            for current_root, _dirs, files in os.walk(root):
                if "model.mud" not in files:
                    continue
                candidate = os.path.join(current_root, "model.mud")
                lowered = candidate.lower()
                if required and not all(token in lowered for token in required):
                    continue
                if optional and not any(token in lowered for token in optional):
                    # Optional tokens are hints; do not strictly require them.
                    pass
                if required:
                    return candidate

        return None

    def list_installed_model_files(self) -> List[str]:
        results: List[str] = []
        for root in ["/root/models", "/maixapp/share/models"]:
            if not os.path.isdir(root):
                continue
            for current_root, _dirs, files in os.walk(root):
                if "model.mud" in files:
                    results.append(os.path.join(current_root, "model.mud"))
        return sorted(results)
