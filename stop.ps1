<#
.SYNOPSIS
    Stops the Laya web app.

.DESCRIPTION
    Finds and closes any python process running this project's app. Safe to run
    when nothing is started - it says so and exits cleanly.

.EXAMPLE
    .\stop.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'SilentlyContinue'
$repo = $PSScriptRoot

$targets = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*$repo*" -or $_.CommandLine -like '*laya_chat*' }

if (-not $targets) {
    Write-Host ''
    Write-Host '  Nothing was running.' -ForegroundColor DarkGray
    Write-Host ''
    exit 0
}

foreach ($p in $targets) {
    Stop-Process -Id $p.ProcessId -Force
    Write-Host "  Stopped PID $($p.ProcessId)" -ForegroundColor Green
}
Write-Host ''
Write-Host '  Done.' -ForegroundColor Green
Write-Host ''
