param(
    [string]$DeviceHost = "10.17.43.1",
    [string]$User = "root",
    [int]$Port = 22,
    [ValidateSet("https://hf-mirror.com", "https://huggingface.co")]
    [string]$HFEndpoint = "https://hf-mirror.com",
    [string]$ModelName,
    [switch]$AllModels,
    [switch]$ForceDownload
)

$ErrorActionPreference = "Stop"

$models = @(
    "Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448-maixcam2",
    "deepseek-r1-distill-qwen-1.5B-maixcam2",
    "Qwen2.5-1.5B-Instruct-maixcam2",
    "Qwen2.5-0.5B-Instruct-maixcam2",
    "whisper-basic-maixcam2",
    "lcm-lora-sdv1-5-320x320-maixcam2",
    "lcm-lora-sdv1-5-maixcam2"
)

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Escape-ShellArg {
    param([string]$Value)
    if ($null -eq $Value) { return "''" }
    return "'" + $Value.Replace("'", "'\''") + "'"
}

function Invoke-Remote {
    param([Parameter(Mandatory = $true)][string]$Command)
    $output = & ssh -p $Port -o StrictHostKeyChecking=accept-new "$User@$DeviceHost" $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Remote command failed: $Command"
    }
    return ($output | Out-String).Trim()
}

function Ensure-HuggingFaceHub {
    Write-Host "Checking huggingface_hub on camera..."
    $checkPy = "import huggingface_hub as h; print(h.__version__)"
    $checkCmd = "/usr/local/bin/python3 -c " + (Escape-ShellArg $checkPy)
    & ssh -p $Port -o StrictHostKeyChecking=accept-new "$User@$DeviceHost" $checkCmd
    if ($LASTEXITCODE -eq 0) {
        return
    }

    Write-Host "Installing huggingface_hub on camera..."
    Invoke-Remote -Command "/usr/local/bin/python3 -m pip install --upgrade 'huggingface_hub>=0.34,<1.0'"
}

function Download-Model {
    param([Parameter(Mandatory = $true)][string]$ModelName)

    $repo = "sipeed/$ModelName"
    $localDir = "/root/models/$ModelName"

    $checkCmd = "find {0} -maxdepth 6 -type f -name 'model.mud' | head -n 1" -f (Escape-ShellArg $localDir)
    $existingModel = ""
    try {
        $existingModel = Invoke-Remote -Command $checkCmd
    }
    catch {
        $existingModel = ""
    }

    if (-not $ForceDownload -and $existingModel) {
        Write-Host "Skip download: model already present at $existingModel"
        return
    }

    Write-Host "Downloading $repo to $localDir ..."

    $localTempPy = Join-Path $env:TEMP "hf_download_model.py"
    $remoteTempPy = "/tmp/hf_download_model.py"
    $pyCode = @"
import os
import shutil
import sys
import threading
import time
from huggingface_hub import snapshot_download

repo_id = sys.argv[1]
local_dir = sys.argv[2]

def dir_size_mb(path):
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            fp = os.path.join(root, name)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total / (1024 * 1024)

def normalize_layout(base_dir):
    expected = os.path.join(base_dir, "model.mud")
    if os.path.exists(expected):
        return expected

    candidates = []
    for root, _dirs, files in os.walk(base_dir):
        parts = root.split(os.sep)
        if ".cache" in parts:
            continue
        if "model.mud" in files:
            candidates.append(os.path.join(root, "model.mud"))

    if not candidates:
        return None

    if len(candidates) == 1:
        nested_model = candidates[0]
        nested_root = os.path.dirname(nested_model)
        if os.path.abspath(nested_root) != os.path.abspath(base_dir):
            print(f"[POST] Normalize layout from {nested_root} to {base_dir}", flush=True)
            for item in os.listdir(nested_root):
                src = os.path.join(nested_root, item)
                dst = os.path.join(base_dir, item)
                if os.path.exists(dst):
                    continue
                shutil.move(src, dst)
            current = nested_root
            while os.path.abspath(current) != os.path.abspath(base_dir):
                try:
                    os.rmdir(current)
                except OSError:
                    break
                current = os.path.dirname(current)
        return os.path.join(base_dir, "model.mud") if os.path.exists(os.path.join(base_dir, "model.mud")) else nested_model

    print("[POST] Multiple model.mud found:", flush=True)
    for p in candidates:
        print(f"[POST] - {p}", flush=True)
    return candidates[0]

print(f"[START] repo={repo_id}", flush=True)
print(f"[START] local_dir={local_dir}", flush=True)

stop_evt = threading.Event()

def progress_worker():
    started = time.time()
    while not stop_evt.wait(15):
        size = dir_size_mb(local_dir)
        elapsed = int(time.time() - started)
        print(f"[PROGRESS] elapsed={elapsed}s size={size:.1f}MB", flush=True)

thread = threading.Thread(target=progress_worker, daemon=True)
thread.start()

try:
    snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir,
    )
finally:
    stop_evt.set()
    thread.join(timeout=1.0)

resolved = normalize_layout(local_dir)
if not resolved:
    raise RuntimeError("Download finished but no model.mud was found")

print(f"[DONE] model={resolved}", flush=True)

print(f"DONE: {local_dir}")
"@

    try {
        Set-Content -Path $localTempPy -Value $pyCode -Encoding UTF8

        & scp -P $Port $localTempPy "$User@$DeviceHost`:$remoteTempPy"
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to upload helper script to camera"
        }

        $secondaryEndpoint = if ($HFEndpoint -eq "https://hf-mirror.com") { "https://huggingface.co" } else { "https://hf-mirror.com" }
        $endpoints = @($HFEndpoint, $secondaryEndpoint)
        $downloadOk = $false

        foreach ($ep in $endpoints) {
            Write-Host "Trying endpoint: $ep"
            $runCmd = "PYTHONUNBUFFERED=1 HF_ENDPOINT={0} /usr/local/bin/python3 {1} {2} {3}" -f (Escape-ShellArg $ep), (Escape-ShellArg $remoteTempPy), (Escape-ShellArg $repo), (Escape-ShellArg $localDir)
            & ssh -p $Port -o StrictHostKeyChecking=accept-new "$User@$DeviceHost" $runCmd
            if ($LASTEXITCODE -eq 0) {
                $downloadOk = $true
                break
            }
            else {
                Write-Warning "Download attempt failed on endpoint: $ep"
            }
        }

        if (-not $downloadOk) {
            throw "Model download failed for $ModelName on all endpoints"
        }
    }
    finally {
        & ssh -p $Port -o StrictHostKeyChecking=accept-new "$User@$DeviceHost" ("rm -f " + (Escape-ShellArg $remoteTempPy)) | Out-Null
        if (Test-Path $localTempPy) {
            Remove-Item -Path $localTempPy -Force
        }
    }

    Write-Host "Download completed: $localDir"
}

function List-InstalledModels {
    Write-Host "Installed model.mud files on camera:"
    $cmd = "find /root/models -maxdepth 8 -type f -name 'model.mud' | sort"
    $res = Invoke-Remote -Command $cmd
    if (-not $res) {
        Write-Host "(none found)"
    }
    else {
        Write-Host $res
    }
}

function Show-Menu {
    Write-Host ""
    Write-Host "====== Model Download Menu ======"
    for ($i = 0; $i -lt $models.Count; $i++) {
        Write-Host "$($i + 1)) Download $($models[$i])"
    }
    Write-Host "L) List installed models on camera"
    Write-Host "E) Change HF endpoint (current: $HFEndpoint)"
    Write-Host "Q) Quit"
    Write-Host "================================="
}

Assert-Command -Name "ssh"
Assert-Command -Name "scp"
Ensure-HuggingFaceHub

if ($ModelName -and $AllModels) {
    throw "Use either -ModelName or -AllModels, not both."
}

if ($ModelName) {
    $match = $models | Where-Object { $_.ToLowerInvariant() -eq $ModelName.ToLowerInvariant() } | Select-Object -First 1
    if (-not $match) {
        throw "Unknown model name: $ModelName"
    }

    Download-Model -ModelName $match
    exit 0
}

if ($AllModels) {
    $failed = @()
    foreach ($m in $models) {
        try {
            Download-Model -ModelName $m
        }
        catch {
            Write-Error $_
            $failed += $m
        }
    }

    if ($failed.Count -gt 0) {
        throw ("Some model downloads failed: " + ($failed -join ", "))
    }

    Write-Host "All model downloads completed successfully."
    exit 0
}

while ($true) {
    Show-Menu
    $choice = (Read-Host "Choose an option").Trim()

    if ($choice -match '^[Qq]$') {
        Write-Host "Bye."
        break
    }

    if ($choice -match '^[Ll]$') {
        try {
            List-InstalledModels
        }
        catch {
            Write-Error $_
        }
        continue
    }

    if ($choice -match '^[Ee]$') {
        $newEndpoint = Read-Host "HF endpoint (https://hf-mirror.com or https://huggingface.co)"
        if ($newEndpoint -in @("https://hf-mirror.com", "https://huggingface.co")) {
            $HFEndpoint = $newEndpoint
            Write-Host "Endpoint updated: $HFEndpoint"
        }
        else {
            Write-Warning "Invalid endpoint."
        }
        continue
    }

    $index = 0
    if (-not [int]::TryParse($choice, [ref]$index)) {
        Write-Warning "Invalid choice"
        continue
    }

    if ($index -lt 1 -or $index -gt $models.Count) {
        Write-Warning "Invalid model index"
        continue
    }

    $model = $models[$index - 1]
    try {
        Download-Model -ModelName $model
    }
    catch {
        Write-Error $_
    }
}
