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

Assert-Command -Name "ssh"

function Invoke-RemoteWithRetry {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [int]$Retries = 20,
        [int]$DelaySeconds = 1
    )

    for ($i = 1; $i -le $Retries; $i++) {
        $output = & ssh -p $Port -o StrictHostKeyChecking=accept-new "$User@$DeviceHost" $Command 2>$null
        if ($LASTEXITCODE -eq 0) {
            return ,$output
        }
        Start-Sleep -Seconds $DelaySeconds
    }

    throw "Remote command failed after $Retries attempts: $Command"
}

Write-Host "Starting VLM daemon on $User@$DeviceHost ..."
& ssh -p $Port -o StrictHostKeyChecking=accept-new "$User@$DeviceHost" "cd '$RemoteSkillDir'; chmod +x start_daemon.sh stop_daemon.sh status_daemon.sh; ./start_daemon.sh"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to start VLM daemon."
}

Write-Host "Checking health endpoint ..."
$health = Invoke-RemoteWithRetry -Command "curl -s http://127.0.0.1:18080/health"
$healthText = ($health | Out-String).Trim()
Write-Host $healthText

Write-Host "Listing available models ..."
$models = Invoke-RemoteWithRetry -Command "curl -s http://127.0.0.1:18080/models"
$modelsText = ($models | Out-String).Trim()
Write-Host $modelsText

Write-Host "VLM daemon smoke test completed."
