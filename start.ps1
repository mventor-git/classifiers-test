<#
.SYNOPSIS
    Starts the Laya web app.

.DESCRIPTION
    Checks the environment, then serves the Gradio app on http://127.0.0.1:7860.
    The first start after a clone is slow (the model loads onto the GPU);
    after that it takes a few seconds.

.EXAMPLE
    .\start.ps1
    .\start.ps1 -Port 7861
    .\start.ps1 -Device cpu
#>
[CmdletBinding()]
param(
    [int]$Port,
    [ValidateSet('cuda', 'cpu')]
    [string]$Device = 'cuda',
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$repo = $PSScriptRoot
Set-Location $repo

$venvPython = Join-Path $repo '.venv\Scripts\python.exe'
$app       = Join-Path $repo 'src\laya_chat\app.py'

function Stop-With([string]$msg) {
    Write-Host ''
    Write-Host "  $msg" -ForegroundColor Red
    Write-Host ''
    Read-Host '  Press Enter to close'
    exit 1
}

Write-Host ''
Write-Host '  ============================================================' -ForegroundColor DarkYellow
Write-Host '   Laya  -  local decision engine' -ForegroundColor Yellow
Write-Host '  ============================================================' -ForegroundColor DarkYellow
Write-Host ''

if (-not (Test-Path -LiteralPath $venvPython)) {
    Stop-With "No virtual environment at .venv . Run .\setup.cmd once first."
}
if (-not (Test-Path -LiteralPath $app)) { Stop-With "Cannot find src\laya_chat\app.py ." }

# Keep torch on the physical cores, not the 12 logical threads.
$env:LAYA_DEVICE = $Device
$env:LAYA_THREADS = '6'
$env:PYTHONIOENCODING = 'utf-8'
if ($Port) { $env:LAYA_PORT = "$Port" }

$listenPort = $env:LAYA_PORT
if (-not $listenPort) { $listenPort = '7860' }
$url = "http://127.0.0.1:$listenPort/"

Write-Host "  device   : $Device"
Write-Host "  url      : $url"
Write-Host "  weights  : .data\huggingface  (inside the repo)"
Write-Host ''
Write-Host '  First start loads the model onto the GPU. Please wait.' -ForegroundColor DarkGray
Write-Host '  Press Ctrl+C in this window to stop.' -ForegroundColor DarkGray
Write-Host ''

if (-not $NoBrowser) {
    # Open the browser once the server answers, not before.
    $job = Start-Job -ScriptBlock {
        param($target)
        for ($i = 0; $i -lt 150; $i++) {
            try {
                Invoke-WebRequest -Uri $target -TimeoutSec 2 -UseBasicParsing | Out-Null
                Start-Process $target
                break
            } catch { Start-Sleep -Seconds 2 }
        }
    } -ArgumentList $url
}

try {
    & $venvPython $app
}
finally {
    if ($job) { Remove-Job $job -Force -ErrorAction SilentlyContinue }
    Write-Host ''
    Write-Host '  Laya stopped.' -ForegroundColor DarkGray
    Write-Host ''
}
