# Maixcam2_Skills

Skills for PicoClaw on Sipeed MaixCAM2 (Python + shell, using MaixPy).

## Useful structure

- Skill folders: each skill folder contains `SKILL.md` (for example `photo-2k`, `person-detect`)
- Shared Python helpers: `python_tools/`
- Windows utility scripts: `0_Configure_ssh.ps1`, `1_update_skills.ps1`
- Quick test scripts: `tests/`

## Shared Python helpers

`python_tools/maix_env.py` exposes `ensure_maix_env()` to initialize `LD_LIBRARY_PATH` before importing `maix` modules.

Recommended pattern in a Python skill:

```python
import os
import sys

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SKILL_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from python_tools.maix_env import ensure_maix_env
ensure_maix_env()

from maix import camera
```

## Utility scripts

### 0_Configure_ssh.ps1

Purpose: configure key-based SSH access from Windows to MaixCAM2.

What it does:
- creates a local `ed25519` key if missing
- appends the public key to `~/.ssh/authorized_keys` on the camera
- validates key-based authentication

Usage:

```powershell
powershell -ExecutionPolicy Bypass -File .\0_Configure_ssh.ps1 -DeviceHost 10.17.43.1 -User root -Port 22
```

Note: the parameter is `DeviceHost` (not `Host`) to avoid a conflict with PowerShell's built-in read-only `$Host` variable.

### 1_update_skills.ps1

Purpose: zip local skills and deploy them to the camera.

What it does:
- detects root-level skill folders (folders containing `SKILL.md`)
- explicitly excludes the `tests/` folder
- includes `python_tools/` (shared module)
- uploads the zip to `/root/.picoclaw/workspace/tmp/skills_bundle.zip`
- extracts into `/root/.picoclaw/workspace/skills`, overwriting existing files

Usage:

```powershell
powershell -ExecutionPolicy Bypass -File .\1_update_skills.ps1 -DeviceHost 10.17.43.1 -User root -Port 22
```

## Test scripts

### tests/test_photo2K.ps1

Purpose: run the `photo-2k` Python script directly on the camera without PicoClaw.

What it does:
- opens an SSH session
- changes directory to `"/root/.picoclaw/workspace/"`
- runs `skills/photo-2k/capture.py`

Usage:

```powershell
powershell -ExecutionPolicy Bypass -File .\tests\test_photo2K.ps1 -DeviceHost 10.17.43.1 -User root -Port 22
```

### tests/test_personDetect.ps1

Purpose: run the `person-detect` Python script directly on the camera without PicoClaw.

What it does:
- opens an SSH session
- changes directory to `"/root/.picoclaw/workspace/"`
- runs `skills/person-detect/person_detect.py`
- reads the latest `person_count_*.txt` report and prints detected people count

Usage:

```powershell
powershell -ExecutionPolicy Bypass -File .\tests\test_personDetect.ps1 -DeviceHost 10.17.43.1 -User root -Port 22
```
