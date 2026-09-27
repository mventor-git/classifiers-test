<#
.SYNOPSIS
    Starts the classifiers app.

.DESCRIPTION
    Asks which classifier you want BEFORE anything loads, then serves only that
    one. The choice is not cosmetic: on a 3 GB card the text model takes 1884 MB
    and the image model pushes you to 2781 MB, and a long text call with both
    resident peaks at 2988 of 3072 MB - one allocation away from an out-of-memory
    crash. Picking one means the question never arises.

.EXAMPLE
    .\start.ps1                       # asks which classifier
    .\start.ps1 -Classifier image     # skip the question
    .\start.ps1 -Classifier both      # both tabs, with the VRAM guard active
    .\start.ps1 -Device cpu           # no GPU
#>
[CmdletBinding()]
param(
    [ValidateSet('ask', 'text', 'image', 'both')]
    [string]$Classifier = 'ask',
    [int]$Port,
    [ValidateSet('cuda', 'cpu')]
    [string]$Device = 'cuda',
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$repo = $PSScriptRoot
Set-Location $repo

$venvPython = Join-Path $repo '.venv\Scripts\python.exe'
$app        = Join-Path $repo 'src\laya_chat\app.py'

function Stop-With([string]$msg) {
    Write-Host ''
    Write-Host "  $msg" -ForegroundColor Red
    if ($msg -like '*installer*') {
        Write-Host '  Run:  .\installer.ps1' -ForegroundColor Yellow
    }
    Write-Host ''
    Read-Host '  Press Enter to close'
    exit 1
}

Write-Host ''
Write-Host '  ============================================================' -ForegroundColor DarkYellow
Write-Host '   classifiers' -ForegroundColor Yellow
Write-Host '  ============================================================' -ForegroundColor DarkYellow
Write-Host ''

if (-not (Test-Path -LiteralPath $venvPython)) {
    Stop-With 'No virtual environment found. Run .\installer.ps1 once first.'
}
if (-not (Test-Path -LiteralPath $app)) { Stop-With 'Cannot find src\laya_chat\app.py .' }

# ---------------------------------------------------------------- the question
if ($Classifier -eq 'ask') {
    Write-Host '  Which classifier do you want to load?' -ForegroundColor Cyan
    Write-Host ''
    Write-Host '    1  laya  - text decisions      tickets, emails, messages'
    Write-Host '                            which team, refund asked, sender intent'
    Write-Host '                            322M params, ~85 ms, 1884 MB of VRAM'
    Write-Host ''
    Write-Host '    2  image - AI vs human photo   drop in an image, get ai or hum'
    Write-Host '                            SigLIP, ~70 ms, 402 MB of VRAM'
    Write-Host ''
    Write-Host '    3  both  - both of the above  tabs for both, but they share'
    Write-Host '                            3 GB of VRAM and get very tight'
    Write-Host ''
    $answer = Read-Host '  Choose 1, 2 or 3'
    switch ($answer.Trim()) {
        '1' { $Classifier = 'text' }
        '2' { $Classifier = 'image' }
        '3' { $Classifier = 'both' }
        default {
            Write-Host ''
            Write-Host '  No valid choice, defaulting to the text classifier.' -ForegroundColor Yellow
            $Classifier = 'text'
        }
    }
}

$mode = switch ($Classifier) {
    'text'  { 'Laya text decisions'; 'laya text decisions' }
    'image' { 'AI vs human image detector'; 'AI vs human image detector' }
    'both'  { 'Both classifiers'; 'both classifiers' }
}

$env:CLASSIFIERS = $Classifier
$env:LAYA_DEVICE = $Device
$env:LAYA_THREADS = '6'
$env:PYTHONIOENCODING = 'utf-8'
if ($Port) { $env:LAYA_PORT = "$Port" }

$listenPort = $env:LAYA_PORT
if (-not $listenPort) { $listenPort = '7860' }
$url = "http://127.0.0.1:$listenPort/"

Write-Host ''
Write-Host "  loading   : $mode[0]" -ForegroundColor Green
Write-Host "  device    : $Device"
Write-Host "  url       : $url"
Write-Host '  weights   : .data\huggingface  (inside the project)'
if ($Classifier -eq 'both') {
    Write-Host ''
    Write-Host '  Both tabs share 3 GB of VRAM. The app unloads the image model' -ForegroundColor Yellow
    Write-Host '  automatically when a text call needs the headroom.' -ForegroundColor Yellow
}
Write-Host ''
Write-Host '  The first load of a model takes 20-25 seconds. Please wait.' -ForegroundColor DarkGray
Write-Host '  Press Ctrl+C here to stop.' -ForegroundColor DarkGray
Write-Host ''

if (-not $NoBrowser) {
    # Open the browser only once the server actually answers.
    $job = Start-Job -ScriptBlock {
        param($target)
        for ($i = 0; $i -lt 180; $i++) {
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
    Write-Host '  Stopped.' -ForegroundColor DarkGray
    Write-Host ''
}
