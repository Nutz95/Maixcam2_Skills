param(
    [string]$DeviceHost = "10.17.43.1",
    [string]$User = "root",
    [int]$Port = 22,
    [string]$RemoteWorkspace = "/root/.picoclaw/workspace",
    [string]$RemoteOutputDir = "/root/.picoclaw/workspace/detection_output"
)

$ErrorActionPreference = "Stop"

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

Assert-Command -Name "ssh"

$remoteScript = "$RemoteWorkspace/skills/person-detect/person_detect.py"
$remoteCmd = "cd '{0}'; test -f '{1}' || {{ echo 'Script not found: {1}'; exit 1; }}; /usr/local/bin/python3 '{1}'" -f $RemoteWorkspace, $remoteScript

Write-Host "Running person-detect test on $User@$DeviceHost ..."
& ssh -p $Port -o StrictHostKeyChecking=accept-new "$User@$DeviceHost" $remoteCmd
if ($LASTEXITCODE -ne 0) {
    throw "person-detect test failed."
}

Write-Host "Collecting detection summary from remote report..."
$latestReportCmd = "ls -1t '{0}'/person_count_*.txt 2>/dev/null | head -n1" -f $RemoteOutputDir
$latestReport = (& ssh -p $Port -o StrictHostKeyChecking=accept-new "$User@$DeviceHost" $latestReportCmd | Out-String).Trim()

if (-not $latestReport) {
    Write-Warning "No person_count report found in $RemoteOutputDir"
    Write-Host "person-detect test finished successfully."
    return
}

$reportContent = (& ssh -p $Port -o StrictHostKeyChecking=accept-new "$User@$DeviceHost" "cat '$latestReport'" | Out-String)
$match = [regex]::Match($reportContent, "(\d+)")
if ($match.Success) {
    $detectedCount = [int]$match.Groups[1].Value
    Write-Host "Detected people count: $detectedCount"
    Write-Host "Summary file: $latestReport"
} else {
    Write-Warning "Could not parse detected people count from report: $latestReport"
}

Write-Host "person-detect test finished successfully."
