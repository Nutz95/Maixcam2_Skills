param(
    [string]$DeviceHost = "10.17.43.1",
    [string]$User = "root",
    [int]$Port = 22,
    [string]$RemoteSkillDir = "/root/.picoclaw/workspace/skills/vlm-daemon"
)

$ErrorActionPreference = "Stop"

$SshOptions = @(
    "-o", "StrictHostKeyChecking=accept-new",
    "-o", "ConnectTimeout=6",
    "-o", "ServerAliveInterval=10",
    "-o", "ServerAliveCountMax=2"
)

# Keep non-ASCII prompts readable when sent through ssh/python.
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

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
    $output = & ssh -p $Port @SshOptions "$User@$DeviceHost" $Command
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
    $raw = & ssh -p $Port @SshOptions "$User@$DeviceHost" $cmd 2>&1
    $exitCode = $LASTEXITCODE
    $text = ($raw | Out-String).Trim()

    if (-not $text) {
        throw "Empty API response (exit=$exitCode)"
    }

    $obj = $null
    try {
        $obj = $text | ConvertFrom-Json
    }
    catch {
        if ($exitCode -ne 0) {
            throw "API client failed (exit=$exitCode): $text"
        }
        throw "Invalid JSON response: $text"
    }

    if ($exitCode -ne 0 -or (($obj.PSObject.Properties.Name -contains "ok") -and (-not $obj.ok))) {
        $err = if ($obj.PSObject.Properties.Name -contains "error") { $obj.error } else { $text }
        throw "API error: $err"
    }

    return $obj
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

function Get-ModelLoadTimeoutSeconds {
    param([Parameter(Mandatory = $true)][string]$ModelAlias)

    switch ($ModelAlias.ToLowerInvariant()) {
        "qwen3vl" { return 240 }
        "internvl" { return 180 }
        "smolvlm" { return 90 }
        default { return 180 }
    }
}

function Get-LoadProgressHint {
    # Read the most recent meaningful loader line from daemon logs.
    try {
        $cmd = "cd $(Escape-ShellArg $RemoteSkillDir); if [ -f logs/vlm_daemon.log ]; then tail -n 200 logs/vlm_daemon.log | grep -E 'LLM init start|tokenizer init ok|init [0-9]+ axmodel ok|init post axmodel ok|init vpm axmodel ok|^[[:space:]]*[0-9]+%[[:space:]]*\|' | tail -n 1; fi"
        $line = Invoke-Remote -Command $cmd
        return ($line | Out-String).Trim()
    }
    catch {
        return ""
    }
}

function Wait-ModelLoaded {
    param(
        [Parameter(Mandatory = $true)][string]$ExpectedAlias,
        [int]$TimeoutSeconds = 180,
        [int]$DelaySeconds = 2
    )

    $maxIterations = [Math]::Max(1, [int][Math]::Ceiling($TimeoutSeconds / [double]$DelaySeconds))
    Write-Host "Waiting for model '$ExpectedAlias' to be ready (timeout ${TimeoutSeconds}s)..."

    $lastHint = ""
    for ($i = 1; $i -le $maxIterations; $i++) {
        $status = Get-CurrentModelStatus
        if ($null -ne $status -and $status.loaded -and $status.model_alias -eq $ExpectedAlias) {
            Write-Host "Model '$ExpectedAlias' ready."
            return $status
        }

        $elapsed = $i * $DelaySeconds
        $hint = Get-LoadProgressHint
        if ($hint -and $hint -ne $lastHint) {
            Write-Host ("  - loader: " + $hint)
            $lastHint = $hint
        }

        if ($null -ne $status -and $status.loaded) {
            Write-Host ("  - " + $elapsed + "s: currently loaded='" + $status.model_alias + "', waiting='" + $ExpectedAlias + "'")
        }
        elseif ($null -ne $status) {
            Write-Host ("  - " + $elapsed + "s: daemon ready, model not loaded yet")
        }
        else {
            Write-Host ("  - " + $elapsed + "s: daemon/API not reachable yet")
        }

        Start-Sleep -Seconds $DelaySeconds
    }

    Write-Warning "Timeout while waiting for model '$ExpectedAlias'."

    return $null
}

function Show-DaemonLogs {
    param([int]$Lines = 80)

    try {
        $cmd = "cd $(Escape-ShellArg $RemoteSkillDir); ./status_daemon.sh; echo '--- daemon log tail ---'; tail -n $Lines logs/vlm_daemon.log"
        $out = Invoke-Remote -Command $cmd
        Write-Host $out
    }
    catch {
        Write-Warning "Failed to read daemon logs: $($_.Exception.Message)"
    }
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
                try {
                    $health = Invoke-ApiClient -Args @("health")
                    Write-Host ("API health: " + ($health | ConvertTo-Json -Depth 8 -Compress))
                }
                catch {
                    $msg = $_.Exception.Message
                    Write-Warning ("API health unreachable or invalid response: " + $msg)
                }
            }
            "4" {
                $models = Invoke-ApiClient -Args @("models")
                Write-Host ($models | ConvertTo-Json -Depth 8)
            }
            "5" {
                $model = (Read-Host "Model alias (smolvlm|qwen3vl|internvl)").Trim().ToLowerInvariant()
                if (-not $model) {
                    Write-Warning "Model alias is required."
                    break
                }

                $customModelPath = (Read-Host "Optional custom model path (leave empty to use default/discovery)").Trim()
                if (-not $customModelPath) {
                    $customModelPath = $null
                }

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

                $timeoutSeconds = Get-ModelLoadTimeoutSeconds -ModelAlias $model
                $loadedStatus = Wait-ModelLoaded -ExpectedAlias $model -TimeoutSeconds $timeoutSeconds
                if ($null -eq $loadedStatus) {
                    if ($null -ne $loadError) {
                        Write-Warning "Model load not confirmed for '$model'. Error: $loadError"
                        Show-DaemonLogs
                        break
                    }
                    Write-Warning "Model load not confirmed for '$model' after polling status."
                    Show-DaemonLogs
                    break
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
                if (-not $ask.answer -or $ask.answer -eq "[empty model response]") {
                    Write-Warning "Model returned an empty answer. Try a short ASCII prompt (e.g. 'describe image') and check daemon logs."
                }
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
