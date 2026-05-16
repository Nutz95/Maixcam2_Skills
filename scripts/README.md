# Local Scripts

This folder contains local maintenance scripts for Windows.
These scripts are not deployed to the camera by the deployment workflow.

## downloadModels.ps1

Interactive and non-interactive downloader for MaixCAM2 models from Hugging Face.

### Features

- Download one model from a menu (interactive mode)
- Download one model directly (non-interactive mode)
- Download all listed models in sequence
- Skip re-download when model.mud already exists (default behavior)
- Optional forced re-download with `-ForceDownload`
- Select preferred endpoint: hf-mirror or official Hugging Face
- Automatic fallback to the other endpoint if the first one fails
- Auto-install compatible huggingface_hub version on the camera

### Usage

Interactive menu:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\downloadModels.ps1 -DeviceHost 10.17.43.1 -User root -Port 22
```

Direct download of one model:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\downloadModels.ps1 -DeviceHost 10.17.43.1 -User root -Port 22 -HFEndpoint https://hf-mirror.com -ModelName "Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448-maixcam2"
```

Download all models:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\downloadModels.ps1 -DeviceHost 10.17.43.1 -User root -Port 22 -HFEndpoint https://hf-mirror.com -AllModels
```

Force re-download of one model (ignore existing local model):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\downloadModels.ps1 -DeviceHost 10.17.43.1 -User root -Port 22 -HFEndpoint https://huggingface.co -ModelName "Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448-maixcam2" -ForceDownload
```

### One command per model

Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448-maixcam2

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\downloadModels.ps1 -DeviceHost 10.17.43.1 -User root -Port 22 -HFEndpoint https://hf-mirror.com -ModelName "Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448-maixcam2"
```

deepseek-r1-distill-qwen-1.5B-maixcam2

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\downloadModels.ps1 -DeviceHost 10.17.43.1 -User root -Port 22 -HFEndpoint https://hf-mirror.com -ModelName "deepseek-r1-distill-qwen-1.5B-maixcam2"
```

Qwen2.5-1.5B-Instruct-maixcam2

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\downloadModels.ps1 -DeviceHost 10.17.43.1 -User root -Port 22 -HFEndpoint https://hf-mirror.com -ModelName "Qwen2.5-1.5B-Instruct-maixcam2"
```

Qwen2.5-0.5B-Instruct-maixcam2

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\downloadModels.ps1 -DeviceHost 10.17.43.1 -User root -Port 22 -HFEndpoint https://hf-mirror.com -ModelName "Qwen2.5-0.5B-Instruct-maixcam2"
```

whisper-basic-maixcam2

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\downloadModels.ps1 -DeviceHost 10.17.43.1 -User root -Port 22 -HFEndpoint https://hf-mirror.com -ModelName "whisper-basic-maixcam2"
```

lcm-lora-sdv1-5-320x320-maixcam2

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\downloadModels.ps1 -DeviceHost 10.17.43.1 -User root -Port 22 -HFEndpoint https://hf-mirror.com -ModelName "lcm-lora-sdv1-5-320x320-maixcam2"
```

lcm-lora-sdv1-5-maixcam2

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\downloadModels.ps1 -DeviceHost 10.17.43.1 -User root -Port 22 -HFEndpoint https://hf-mirror.com -ModelName "lcm-lora-sdv1-5-maixcam2"
```

### Notes

- If your network blocks one endpoint, the script retries with the other endpoint.
- By default, existing models are not downloaded again.
- Large model downloads can take a long time.
- Download target on camera: /root/models/<model-name>
