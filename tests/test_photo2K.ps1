param(
    [string]$DeviceHost = "10.17.43.1",
    [string]$User = "root",
    [int]$Port = 22,
    [string]$RemoteWorkspace = "/root/.picoclaw/workspace",
    [string]$OutputPath = "/root/.picoclaw/workspace/capture_photo_2k_test.jpg"
)

$ErrorActionPreference = "Stop"

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Commande requise introuvable: $Name"
    }
}

Assert-Command -Name "ssh"

$remoteScript = "$RemoteWorkspace/skills/photo-2k/capture.py"
$remoteCmd = "cd '{0}'; test -f '{1}' || {{ echo 'Script introuvable: {1}'; exit 1; }}; /usr/local/bin/python3 '{1}' '{2}'" -f $RemoteWorkspace, $remoteScript, $OutputPath

Write-Host "Execution du test photo-2k sur $User@$DeviceHost ..."
& ssh -p $Port -o StrictHostKeyChecking=accept-new "$User@$DeviceHost" $remoteCmd
if ($LASTEXITCODE -ne 0) {
    throw "Le test photo-2k a echoue."
}

Write-Host "Test photo-2k termine avec succes."
Write-Host "Image de sortie: $OutputPath"
