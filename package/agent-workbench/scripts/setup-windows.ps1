[CmdletBinding()]
param([string]$Distribution = 'Ubuntu-24.04')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    throw 'WSL is unavailable. Run this script in an Administrator PowerShell window after enabling WSL.'
}
$distros = ((wsl.exe --list --quiet) -join "`n") -replace "`0", ''
if ($distros -notmatch [regex]::Escape($Distribution)) {
    wsl.exe --install --distribution $Distribution --no-launch
    if ($LASTEXITCODE -ne 0) { throw 'WSL installation failed; inspect the Windows error above.' }
    Write-Host "Open $Distribution once to create its Linux user, reboot if Windows requests it, then rerun this script."
    exit 2
}
$linuxSource = (wsl.exe -d $Distribution -- wslpath -a $root).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Could not resolve the package path in WSL.' }
# Transfer via argv rather than interpolating a Windows path into shell code.
wsl.exe -d $Distribution -- bash -lc 'set -e; dest="$HOME/agent-workbench"; mkdir -p "$dest"; cp -R "$1"/. "$dest"/; exec bash "$dest/scripts/setup.sh"' workbench-setup $linuxSource
if ($LASTEXITCODE -ne 0) { throw "Linux setup needs attention (exit $LASTEXITCODE)." }
Write-Host 'Installed in the Linux filesystem at ~/agent-workbench. Open Ubuntu and follow docs/GUIDE.md.'
