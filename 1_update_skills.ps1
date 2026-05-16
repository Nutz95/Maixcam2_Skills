param(
    [string]$DeviceHost = "10.17.43.1",
    [string]$User = "root",
    [int]$Port = 22,
    [string]$RemoteWorkspace = "/root/.picoclaw/workspace"
)

$ErrorActionPreference = "Stop"
$excludedDirs = @("tests")

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Commande requise introuvable: $Name"
    }
}

Assert-Command -Name "ssh"
Assert-Command -Name "scp"
Assert-Command -Name "python"

$repoRoot = $PSScriptRoot
$skillDirs = Get-ChildItem -Path $repoRoot -Directory | Where-Object {
    (Test-Path (Join-Path $_.FullName "SKILL.md")) -and ($excludedDirs -notcontains $_.Name)
}
$sharedDirs = @("python_tools") | Where-Object {
    Test-Path (Join-Path $repoRoot $_) -PathType Container
}

if (-not $skillDirs -or $skillDirs.Count -eq 0) {
    throw "Aucun dossier de skill detecte a la racine (dossier contenant SKILL.md)."
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$stagingRoot = Join-Path $env:TEMP "maix_skills_bundle_$timestamp"
$zipPath = Join-Path $env:TEMP "maix_skills_bundle.zip"
$zipBuilderPath = Join-Path $env:TEMP "maix_skills_zip_builder.py"

if (Test-Path $stagingRoot) {
    Remove-Item -Path $stagingRoot -Recurse -Force
}
if (Test-Path $zipPath) {
    Remove-Item -Path $zipPath -Force
}

New-Item -Path $stagingRoot -ItemType Directory -Force | Out-Null

try {
    foreach ($dir in $skillDirs) {
        $dest = Join-Path $stagingRoot $dir.Name
        Copy-Item -Path $dir.FullName -Destination $dest -Recurse -Force
    }

    foreach ($shared in $sharedDirs) {
        $src = Join-Path $repoRoot $shared
        $dest = Join-Path $stagingRoot $shared
        Copy-Item -Path $src -Destination $dest -Recurse -Force
    }

    $zipBuilder = @"
import os
import sys
import zipfile

staging_root = sys.argv[1]
zip_path = sys.argv[2]

with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for root, _dirs, files in os.walk(staging_root):
        for filename in files:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, staging_root)
            arcname = rel_path.replace(os.sep, "/")
            zf.write(full_path, arcname)
"@

    Set-Content -Path $zipBuilderPath -Value $zipBuilder -Encoding UTF8
    & python $zipBuilderPath $stagingRoot $zipPath
    if ($LASTEXITCODE -ne 0) {
        throw "Echec de creation du zip de skills"
    }

    $remoteTmp = "$RemoteWorkspace/tmp"
    $remoteSkills = "$RemoteWorkspace/skills"
    $remoteZip = "$remoteTmp/skills_bundle.zip"

    Write-Host "Preparation du dossier distant..."
    & ssh -p $Port -o StrictHostKeyChecking=accept-new "$User@$DeviceHost" "mkdir -p '$remoteTmp' '$remoteSkills'"
    if ($LASTEXITCODE -ne 0) {
        throw "Echec de creation des dossiers distants"
    }

    Write-Host "Upload du zip vers $remoteZip"
    & scp -P $Port $zipPath "$User@$DeviceHost`:$remoteZip"
    if ($LASTEXITCODE -ne 0) {
        throw "Echec de l'upload du zip"
    }

    Write-Host "Decompression dans $remoteSkills"
    $prepareCmd = "mkdir -p '{0}' '{1}'" -f $remoteTmp, $remoteSkills
    & ssh -p $Port -o StrictHostKeyChecking=accept-new "$User@$DeviceHost" $prepareCmd
    if ($LASTEXITCODE -ne 0) {
        throw "Echec de preparation avant decompression distante"
    }

    & ssh -p $Port -o StrictHostKeyChecking=accept-new "$User@$DeviceHost" "command -v unzip >/dev/null 2>&1"
    if ($LASTEXITCODE -eq 0) {
        $unzipCmd = "unzip -o '{0}' -d '{1}'" -f $remoteZip, $remoteSkills
        & ssh -p $Port -o StrictHostKeyChecking=accept-new "$User@$DeviceHost" $unzipCmd
        if ($LASTEXITCODE -ne 0) {
            throw "Echec de la decompression distante avec unzip"
        }
    }
    else {
        $pythonCmd = "/usr/local/bin/python3 -m zipfile -e '{0}' '{1}'" -f $remoteZip, $remoteSkills
        & ssh -p $Port -o StrictHostKeyChecking=accept-new "$User@$DeviceHost" $pythonCmd
        if ($LASTEXITCODE -ne 0) {
            throw "Echec de la decompression distante avec python3"
        }
    }

    Write-Host "Mise a jour des skills terminee avec succes."
    Write-Host "Skills deployes:"
    $skillDirs | ForEach-Object { Write-Host "- $($_.Name)" }
    $sharedDirs | ForEach-Object { Write-Host "- $($_) (shared)" }
}
finally {
    if (Test-Path $stagingRoot) {
        Remove-Item -Path $stagingRoot -Recurse -Force
    }
    if (Test-Path $zipBuilderPath) {
        Remove-Item -Path $zipBuilderPath -Force
    }
}
