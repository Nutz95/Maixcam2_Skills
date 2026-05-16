param(
    [string]$DeviceHost = "10.17.43.1",
    [string]$User = "root",
    [int]$Port = 22,
    [string]$KeyPath = "$HOME/.ssh/id_ed25519"
)

$ErrorActionPreference = "Stop"

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Commande requise introuvable: $Name"
    }
}

Assert-Command -Name "ssh-keygen"
Assert-Command -Name "ssh"

$sshDir = Split-Path -Parent $KeyPath
if (-not (Test-Path $sshDir)) {
    New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
}

if (-not (Test-Path $KeyPath)) {
    Write-Host "Creation d'une cle SSH locale: $KeyPath"
    & ssh-keygen -t ed25519 -f $KeyPath -N ""
    if ($LASTEXITCODE -ne 0) {
        throw "Echec de la generation de cle SSH"
    }
} else {
    Write-Host "Cle SSH existante detectee: $KeyPath"
}

$pubKeyPath = "$KeyPath.pub"
if (-not (Test-Path $pubKeyPath)) {
    throw "Cle publique introuvable: $pubKeyPath"
}

if (-not (Get-Module -ListAvailable -Name Posh-SSH)) {
    Write-Host "Installation du module Posh-SSH (CurrentUser)..."
    Install-Module -Name Posh-SSH -Scope CurrentUser -Force -AllowClobber
}

Import-Module Posh-SSH -ErrorAction Stop

$password = Read-Host "Mot de passe SSH pour $User@$DeviceHost" -AsSecureString
$credential = New-Object System.Management.Automation.PSCredential($User, $password)
$pubKey = Get-Content -Path $pubKeyPath -Raw
$pubKeyEscaped = $pubKey.Trim().Replace("'", "'\''")

Write-Host "Connexion a $DeviceHost pour installer la cle publique..."
$session = New-SSHSession -ComputerName $DeviceHost -Port $Port -Credential $credential -AcceptKey
try {
    $cmd = "umask 077; mkdir -p ~/.ssh; touch ~/.ssh/authorized_keys; grep -F -- '$pubKeyEscaped' ~/.ssh/authorized_keys >/dev/null 2>&1 || echo '$pubKeyEscaped' >> ~/.ssh/authorized_keys"
    $result = Invoke-SSHCommand -SessionId $session.SessionId -Command $cmd
    if ($result.ExitStatus -ne 0) {
        throw "Echec de l'ajout de la cle publique dans authorized_keys"
    }
} finally {
    Remove-SSHSession -SessionId $session.SessionId | Out-Null
}

Write-Host "Verification de l'authentification par cle..."
& ssh -p $Port -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$User@$DeviceHost" "echo SSH_KEY_OK"
if ($LASTEXITCODE -ne 0) {
    throw "La verification par cle a echoue. Verifiez l'IP/utilisateur/mot de passe initial."
}

Write-Host "Configuration SSH terminee. Les prochaines connexions n'exigeront plus de mot de passe."
