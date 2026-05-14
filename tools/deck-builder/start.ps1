# Deck Builder one-shot launcher.
# Usage:  pwsh -ExecutionPolicy Bypass -File .\start.ps1
#   or:   .\start.ps1   (from inside tools/deck-builder/)
#
# What it does:
#   1. Creates / activates a venv next to this script
#   2. Installs requirements
#   3. Starts the server (which opens http://localhost:8765 in your browser)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$venv = Join-Path $PSScriptRoot ".venv"
$python = Join-Path $venv "Scripts\python.exe"

if (-not (Test-Path $python)) {
  Write-Host "[deck-builder] creating venv at $venv ..." -ForegroundColor Cyan
  py -3 -m venv $venv
}

Write-Host "[deck-builder] installing requirements ..." -ForegroundColor Cyan
& $python -m pip install -q -r requirements.txt

# Verify Azure CLI login (best-effort; warn but don't block)
$az = Get-Command az -ErrorAction SilentlyContinue
if ($az) {
  $acct = (& az account show 2>$null) | ConvertFrom-Json -ErrorAction SilentlyContinue
  if (-not $acct) {
    Write-Host "[deck-builder] WARNING: not logged in to Azure CLI." -ForegroundColor Yellow
    Write-Host "             run 'az login' (or 'az login --tenant <id>') before generating decks." -ForegroundColor Yellow
  } else {
    Write-Host ("[deck-builder] az login OK (tenant {0})" -f $acct.tenantId) -ForegroundColor Green
  }
} else {
  Write-Host "[deck-builder] WARNING: 'az' CLI not found. Install from https://aka.ms/azcli" -ForegroundColor Yellow
}

Write-Host "[deck-builder] starting server ..." -ForegroundColor Cyan
& $python server.py
