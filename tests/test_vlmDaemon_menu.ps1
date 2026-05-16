param(
    [string]$DeviceHost = "10.17.43.1",
    [string]$User = "root",
    [int]$Port = 22,
    [string]$RemoteSkillDir = "/root/.picoclaw/workspace/skills/vlm-daemon"
)

$ErrorActionPreference = "Stop"

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

function Invoke-ApiClient {
    param([Parameter(Mandatory = $true)][string[]]$Args)

    $parts = @("/usr/local/bin/python3", (Escape-ShellArg "$RemoteSkillDir/api_client.py"))
    foreach ($arg in $Args) {
        $parts += (Escape-ShellArg $arg)
    }

    $cmd = "cd " + (Escape-ShellArg $RemoteSkillDir) + "; " + ($parts -join " ")
    $raw = Invoke-Remote -Command $cmd
    if (-not $raw) {
        throw "Empty API response"
    }

    try {
        return $raw | ConvertFrom-Json
    }
    catch {
        throw "Invalid JSON response: $raw"
    }
}

function Get-CurrentModelStatus {
    try {
        $models = Invoke-ApiClient -Args @("models")
        return $models.current
    }
    catch {
        return $null
    }
}

function Wait-ModelLoaded {
    param(
        [Parameter(Mandatory = $true)][string]$ExpectedAlias,
        [int]$Retries = 30,
        [int]$DelaySeconds = 1
    )

    for ($i = 1; $i -le $Retries; $i++) {
        $status = Get-CurrentModelStatus
        if ($null -ne $status -and $status.loaded -and $status.model_alias -eq $ExpectedAlias) {
            return $status
        }
        Start-Sleep -Seconds $DelaySeconds
    }

    return $null
}

function Show-Menu {
    Write-Host ""
    Write-Host "========== VLM Daemon Menu =========="
    Write-Host "1) Start daemon"
    Write-Host "2) Stop daemon"
    Write-Host "3) Status"
    Write-Host "4) List models"
    Write-Host "5) Load model"
    Write-Host "6) Unload model"
    Write-Host "7) Capture + ask (2-step: /capture then /ask)"
    Write-Host "8) Exit"
    Write-Host "====================================="
}

function Stop-VLMDaemonGracefully {
    Write-Host "Graceful shutdown: unload model and stop daemon..."
    try {
        $res = Invoke-ApiClient -Args @("unload")
        Write-Host ("Unload result: " + ($res | ConvertTo-Json -Depth 6 -Compress))
    }
    catch {
        Write-Warning "Unload request failed (daemon may already be down): $($_.Exception.Message)"
    }

    try {
        $out = Invoke-Remote -Command "cd $(Escape-ShellArg $RemoteSkillDir); ./stop_daemon.sh"
        Write-Host $out
    }
    catch {
        Write-Warning "Stop daemon failed: $($_.Exception.Message)"
    }
}

Assert-Command -Name "ssh"

$shouldExit = $false
while ($true) {
    Show-Menu
    $choice = Read-Host "Choose an option"

    try {
        switch ($choice) {
            "1" {
                $out = Invoke-Remote -Command "cd $(Escape-ShellArg $RemoteSkillDir); chmod +x start_daemon.sh stop_daemon.sh status_daemon.sh; ./start_daemon.sh"
                Write-Host $out
            }
            "2" {
                $out = Invoke-Remote -Command "cd $(Escape-ShellArg $RemoteSkillDir); ./stop_daemon.sh"
                Write-Host $out
            }
            "3" {
                $status = Invoke-Remote -Command "cd $(Escape-ShellArg $RemoteSkillDir); ./status_daemon.sh"
                Write-Host "Daemon shell status: $status"
                $health = Invoke-ApiClient -Args @("health")
                Write-Host ("API health: " + ($health | ConvertTo-Json -Depth 8 -Compress))
            }
            "4" {
                $models = Invoke-ApiClient -Args @("models")
                Write-Host ($models | ConvertTo-Json -Depth 8)
            }
            "5" {
                $model = Read-Host "Model alias (smolvlm|qwen3vl|internvl)"
                if (-not $model) {
                    Write-Warning "Model alias is required."
                    break
                }

                $customModelPath = Read-Host "Optional custom model path (leave empty to use default/discovery)"

                $loadError = $null
                try {
                    $loadArgs = @("load", "--model", $model)
                    if ($customModelPath) {
                        $loadArgs += @("--model-path", $customModelPath)
                    }
                    $loaded = Invoke-ApiClient -Args $loadArgs
                    Write-Host ($loaded | ConvertTo-Json -Depth 8)
                }
                catch {
                    # Large model init can transiently drop SSH; verify by polling daemon status.
                    $loadError = $_
                    Write-Warning "Load call failed, checking model status..."
                }

                $loadedStatus = Wait-ModelLoaded -ExpectedAlias $model
                if ($null -eq $loadedStatus) {
                    if ($null -ne $loadError) {
                        throw "Model load not confirmed for '$model'. Original error: $loadError"
                    }
                    throw "Model load not confirmed for '$model' after polling status."
                }

                Write-Host ("Model loaded: " + ($loadedStatus | ConvertTo-Json -Depth 6 -Compress))
            }
            "6" {
                $res = Invoke-ApiClient -Args @("unload")
                Write-Host ($res | ConvertTo-Json -Depth 8)
            }
            "7" {
                $capture = Invoke-ApiClient -Args @("capture")
                if (-not $capture.ok) {
                    throw "Capture failed: $($capture | ConvertTo-Json -Depth 8 -Compress)"
                }
                $imgPath = $capture.image_path
                Write-Host "Captured image: $imgPath"

                $question = Read-Host "Prompt/question for VLM"
                if (-not $question) {
                    Write-Warning "Prompt is required."
                    break
                }

                $ask = Invoke-ApiClient -Args @("ask", "--question", $question, "--image-path", $imgPath)
                Write-Host ($ask | ConvertTo-Json -Depth 10)
            }
            "8" {
                Stop-VLMDaemonGracefully
                Write-Host "Bye."
                $shouldExit = $true
            }
            default {
                Write-Warning "Invalid choice."
            }
        }
    }
    catch {
        Write-Error $_
    }

    if ($shouldExit) {
        break
    }
}
