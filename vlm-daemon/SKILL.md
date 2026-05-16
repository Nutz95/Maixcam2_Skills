# vlm-daemon - API daemon for VLM models on MaixCAM2

## Description
This skill starts and manages a background Flask daemon that exposes VLM inference and 2K capture APIs.

A single skill can cover multiple actions. This skill includes:
- start daemon
- stop daemon
- check daemon status and loaded model
- list available VLM models
- load/unload VLM model
- capture 2K image
- capture + ask question on image

## Preferred tools for agents
Use these scripts first, not ad-hoc process grep commands:
- ./start_daemon.sh
- ./stop_daemon.sh
- ./status_daemon.sh
- ./vlmctl.sh

For autonomous agents (picoclaw), always use ./vlmctl.sh because it encapsulates the API calls and returns stable output.

## IMPORTANT: autoload at startup
When the daemon starts, it **automatically loads `qwen3vl`** as the default model.
The `/health` endpoint confirms this via the `autoload.ok` field.
Do NOT assume no model is loaded just because you haven't explicitly loaded one.
Always call `/health` or `/models` to check the real current state.

## Supported VLM models
| alias | class | description |
|-------|-------|-------------|
| `qwen3vl` | `nn.Qwen3VL` | Qwen3-VL 2B Int4 — loaded by default at startup |
| `internvl` | `nn.InternVL` | InternVL2.5 1B |
| `smolvlm` | `nn.SmolVLM` | SmolVLM 256M instruct |

## Start daemon

```bash
cd /root/.picoclaw/workspace/skills/vlm-daemon
chmod +x start_daemon.sh stop_daemon.sh status_daemon.sh vlmctl.sh
./start_daemon.sh
```

Default API endpoint: `http://127.0.0.1:18080`

## Stop daemon

```bash
cd /root/.picoclaw/workspace/skills/vlm-daemon
./stop_daemon.sh
```

## Status

```bash
cd /root/.picoclaw/workspace/skills/vlm-daemon
./status_daemon.sh
```

Expected output fields:
- status=running|stopped|stale_pid
- api_ok=true|false
- api_status=running|unreachable|...
- model_loaded=true|false
- model_alias=qwen3vl|internvl|smolvlm|none
- autoload_ok=true|false (when available)

Do not rely only on process listing (ps/grep). A running process is not sufficient: API may still be unavailable.

## Fast control interface (recommended)

```bash
cd /root/.picoclaw/workspace/skills/vlm-daemon

# daemon
./vlmctl.sh start
./vlmctl.sh status
./vlmctl.sh stop

# model
./vlmctl.sh load qwen3vl
./vlmctl.sh load internvl
./vlmctl.sh load smolvlm
./vlmctl.sh models
./vlmctl.sh unload

# vision
./vlmctl.sh ask "Describe the scene"
./vlmctl.sh ask-image /maixapp/share/picture/2024.1.1/ssd_car.jpg "What is visible?"
```

For natural-language user request "charge qwen3vl":
1) ./vlmctl.sh status
2) if daemon not running: ./vlmctl.sh start, wait 2-5s, then ./vlmctl.sh status
3) ./vlmctl.sh load qwen3vl
4) ./vlmctl.sh status

For "prends une photo et répond":
1) ./vlmctl.sh status
2) if no model loaded: ./vlmctl.sh load qwen3vl
3) ./vlmctl.sh ask "<question>"

## Check daemon state (always do this first)

To know if the daemon is running and which model is active:

```bash
curl -s http://127.0.0.1:18080/health
```

Example response when daemon is running and qwen3vl is loaded (normal state after start):
```json
{
  "ok": true,
  "status": "running",
  "model": {"loaded": true, "model_alias": "qwen3vl", "model_class": "Qwen3VL"},
  "autoload": {"enabled": true, "model": "qwen3vl", "ok": true}
}
```

Example response when no model is loaded:
```json
{"ok": true, "status": "running", "model": {"loaded": false}}
```

## List available models and current state

```bash
curl -s http://127.0.0.1:18080/models
```

Example response:
```json
{
  "current": {"loaded": true, "model_alias": "qwen3vl"},
  "models": {
    "supported": [
      {"alias": "qwen3vl", "available": true, "description": "Qwen3-VL 2B Int4 model"},
      {"alias": "internvl", "available": true, "description": "InternVL2.5 1B model"},
      {"alias": "smolvlm", "available": true, "description": "SmolVLM 256M instruct"}
    ]
  }
}
```

`current.loaded = true` means a model is active. `current.model_alias` is the name of the loaded model.

## Load a model

Loading a model automatically unloads any currently loaded model first.

```bash
curl -s -X POST http://127.0.0.1:18080/models/load \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3vl"}'
```

Valid aliases: `qwen3vl`, `internvl`, `smolvlm`

Example response:
```json
{"ok": true, "message": "model_loaded", "model": {"loaded": true, "model_alias": "qwen3vl"}}
```

## Unload model

```bash
curl -s -X POST http://127.0.0.1:18080/models/unload
```

## Capture only (2K photo)

```bash
curl -s -X POST http://127.0.0.1:18080/capture \
  -H 'Content-Type: application/json' \
  -d '{}'
```

Returns: `{"ok": true, "image_path": "/path/to/image.jpg"}`

## Ask a question about a new capture

A model must be loaded first (qwen3vl is loaded by default at startup).

```bash
curl -s -X POST http://127.0.0.1:18080/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Describe the scene","capture_new":true}'
```

Returns: `{"ok": true, "answer": "...", "image_path": "...", "backend": "http_primary"}`

## Ask on an existing image

```bash
curl -s -X POST http://127.0.0.1:18080/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"How many people?","capture_new":false,"image_path":"/root/.picoclaw/workspace/vlm_capture_20260516_000000_2k.jpg"}'
```

## Start / stop daemon

```bash
# start
cd /root/.picoclaw/workspace/skills/vlm-daemon
chmod +x start_daemon.sh stop_daemon.sh status_daemon.sh vlmctl.sh
./start_daemon.sh
# qwen3vl is automatically loaded after start — wait ~20s then check /health

# stop
./stop_daemon.sh

# status
./status_daemon.sh
```
