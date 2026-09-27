<#
.SYNOPSIS
    One-command setup for classifiers-test.

.DESCRIPTION
    Creates a virtual environment, installs the GPU or CPU build of PyTorch chosen
    for THIS machine, installs the pinned dependencies, fetches BOTH models, and
    verifies the whole thing works.

    It is idempotent and it says what it is doing. Re-run it any time: a model
    already on disk is reported as present and not re-downloaded, and a model
    that is missing is fetched.

    The 647 MB text model and the 363 MB image model are deliberately NOT in the
    repository. This script fetches them from Hugging Face into .data\huggingface.

    The image model is fetched with a three-file allowlist. Its repository also
    contains training_args.bin, a pickle that the Hub flags as unsafe -
    unpickling executes arbitrary code, and inference does not need it. An
    allowlist means no pickle ever lands on this machine.

.EXAMPLE
    git clone https://github.com/mventor-git/classifiers-test
    cd classifiers-test
    powershell -ExecutionPolicy Bypass -File installer.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File installer.ps1 -Device cpu
    powershell -ExecutionPolicy Bypass -File installer.ps1 -SkipModels
    powershell -ExecutionPolicy Bypass -File installer.ps1 -ForceModels
#>
[CmdletBinding()]
param(
    [ValidateSet('auto', 'cuda', 'cpu')]
    [string]$Device = 'auto',
    [switch]$SkipModels,
    [switch]$ForceModels
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

# torch 2.14 is the last release built for CUDA 12.x. CUDA 13.0 REMOVED Pascal
# (sm_61), so cards older than Turing cannot use a cu128/cu129 build at all.
$CUDA_INDEX = 'https://download.pytorch.org/whl/cu126'
$REQUIRED_PY = '3.12'

function Say($msg, $colour = 'Gray') { Write-Host "  $msg" -ForegroundColor $colour }
function Head($msg) { Write-Host ''; Write-Host "  $msg" -ForegroundColor DarkYellow }
function Die($msg, $hint) {
    Write-Host ''
    Write-Host "  FAILED: $msg" -ForegroundColor Red
    if ($hint) { Write-Host "  $hint" -ForegroundColor Yellow }
    Write-Host ''
    Read-Host '  Press Enter to close'
    exit 1
}

Head 'classifiers-test  -  setup'
Say "folder: $PSScriptRoot"

# ---------------------------------------------------------------- 1. device
if ($Device -eq 'auto') {
    $gpu = Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue |
           Where-Object { $_.Name -match 'NVIDIA' } | Select-Object -First 1
    if ($gpu) {
        $Device = 'cuda'
        Say "found GPU: $($gpu.Name)" 'Green'
    } else {
        $Device = 'cpu'
        Say 'no NVIDIA GPU found - installing the CPU build' 'Yellow'
    }
} else {
    Say "device forced to: $Device" 'Yellow'
}

# ---------------------------------------------------------------- 2. uv
$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Die 'no uv and no python on PATH' 'Install uv:  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"'
    }
    Say 'uv not found, falling back to python -m venv + pip' 'Yellow'
}

$venvPy = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'

function Run-Step($exe, $argList, $what, $canFail) {
    Head $what
    & $exe @argList
    if ($LASTEXITCODE -ne 0 -and -not $canFail) {
        Die $what $null
    }
}

# ---------------------------------------------------------------- 3. venv
if (-not (Test-Path -LiteralPath $venvPy)) {
    if ($uv) { Run-Step 'uv' @('venv', '--python', $REQUIRED_PY, '.venv') "creating a Python $REQUIRED_PY environment" $false }
    else { Run-Step 'python' @('-m', 'venv', '.venv') 'creating a virtual environment' $false }
} else {
    Head 'reusing the existing .venv'
}

# ---------------------------------------------------------------- 4. torch
$torchNow = & $venvPy -c "import torch; print(torch.__version__)" 2>$null
if ($torchNow) {
    Head "torch already installed: $torchNow"
} else {
    if ($uv) {
        if ($Device -eq 'cuda') {
            Run-Step 'uv' @('pip', 'install', '--python', $venvPy, 'torch', 'torchvision', '--index-url', $CUDA_INDEX) 'installing the GPU build of torch + torchvision (a ~2.4 GB download)' $false
        } else {
            Run-Step 'uv' @('pip', 'install', '--python', $venvPy, 'torch', 'torchvision') 'installing the CPU build of torch + torchvision' $false
        }
    } else {
        $base = 'https://download.pytorch.org/whl/cu126'
        if ($Device -eq 'cuda') { Run-Step $venvPy @('-m', 'pip', 'install', 'torch', 'torchvision', '--index-url', $base) 'installing the GPU build of torch + torchvision' $false }
        else { Run-Step $venvPy @('-m', 'pip', 'install', 'torch', 'torchvision') 'installing the CPU build of torch + torchvision' $false }
    }
}

# ---------------------------------------------------------------- 5. rest
if ($uv) { Run-Step 'uv' @('pip', 'install', '--python', $venvPy, '-r', 'requirements.lock.txt') 'installing the pinned dependencies' $false }
else { Run-Step $venvPy @('-m', 'pip', 'install', '-r', 'requirements.lock.txt') 'installing the pinned dependencies' $false }

# ---------------------------------------------------------------- 6. models
if ($SkipModels) {
    Head 'skipping the model download (-SkipModels)'
} else {
    $env:HF_HOME = Join-Path $PSScriptRoot '.data\huggingface'
    $env:HF_HUB_DISABLE_SYMLINKS_WARNING = '1'
    $env:CLASSIFIERS_FORCE = if ($ForceModels) { '1' } else { '0' }

    Head 'checking the models'
    & $venvPy "$PSScriptRoot\tools\fetch_models.py"
    if ($LASTEXITCODE -ne 0) {
        Die 'could not fetch the models' 'Check your internet connection, or download by hand from the pages printed above.'
    }
}

# ---------------------------------------------------------------- 7. verify
Head 'verifying the environment'
& $venvPy -c @"
import sys, torch, laya, gradio, transformers, PIL
print('  python    ', sys.version.split()[0])
print('  torch     ', torch.__version__)
print('  torchvision', __import__('torchvision').__version__)
print('  laya      ', laya.__version__)
print('  gradio    ', gradio.__version__)
print('  transformers', transformers.__version__)
print('  pillow    ', PIL.__version__)
print('  cuda      ', torch.cuda.is_available())
if torch.cuda.is_available():
    free, total = torch.cuda.mem_get_info()
    print('  gpu       ', torch.cuda.get_device_name(0))
    print('  vram      ', f'{free/1024**2:.0f} / {total/1024**2:.0f} MB free')
"@
if ($LASTEXITCODE -ne 0) { Die 'the environment did not import cleanly' $null }

Head 'checking what the classifiers need from the hardware'
& $venvPy -c @"
import torch
if not torch.cuda.is_available():
    print('  CPU only. Everything works, roughly 3x slower per decision.')
else:
    free, total = torch.cuda.mem_get_info()
    print(f'  {free/1024**2:.0f} MB of {total/1024**2:.0f} MB free')
    if free/1024**2 < 1200:
        print('  WARNING: under 1.2 GB free. The text model needs ~1.3 GB and the')
        print('           image model ~400 MB, so close other GPU apps first.')
    else:
        print('  enough room for either classifier.')
"@

Head 'done'
Say 'start and pick your classifier with:   powershell -ExecutionPolicy Bypass -File start.ps1'
Say 'or skip the question:                  .\start.ps1 -Classifier image'
Write-Host ''
