<#
.SYNOPSIS
    One-command setup for laya-beta-test.

.DESCRIPTION
    Creates a virtual environment, installs the GPU or CPU build of PyTorch
    chosen for THIS machine, installs the pinned dependencies, downloads the
    model weights, and verifies the whole thing works.

    The model weights are not in the repository. They are 647 MB of binaries
    that do not belong in git history, so this script fetches them from
    Hugging Face into .data\huggingface instead.

.EXAMPLE
    git clone https://github.com/mventor-git/laya-beta-test
    cd laya-beta-test
    powershell -ExecutionPolicy Bypass -File installer.ps1

.EXAMPLE
    Force the CPU build even on a machine with an NVIDIA card:
    powershell -ExecutionPolicy Bypass -File installer.ps1 -Device cpu
#>
[CmdletBinding()]
param(
    [ValidateSet('auto', 'cuda', 'cpu')]
    [string]$Device = 'auto',
    [switch]$SkipWeights
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

# torch 2.14 is the last release built for CUDA 12.x. CUDA 13.0 REMOVED Pascal
# (sm_61), so cards older than Turing cannot use a cu128/cu129 build at all.
$CUDA_INDEX = 'https://download.pytorch.org/whl/cu126'
$REQUIRED_PY = '3.12'

function Say($msg, $colour = 'Gray') { Write-Host "  $msg" -ForegroundColor $colour }
function Head($msg) {
    Write-Host ''
    Write-Host "  $msg" -ForegroundColor DarkYellow
}

Head 'laya-beta-test  -  setup'
Say "folder: $PSScriptRoot"

# ---------------------------------------------------------------- 1. decide device
if ($Device -eq 'auto') {
    $gpu = Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue |
           Where-Object { $_.Name -match 'NVIDIA' } | Select-Object -First 1
    if ($gpu) {
        $Device = 'cuda'
        Say "found GPU: $($gpu.Name)" 'Green'
    } else {
        $Device = 'cpu'
        Say "no NVIDIA GPU found - installing the CPU build" 'Yellow'
    }
} else {
    Say "device forced to: $Device" 'Yellow'
}
if ($Device -eq 'cuda') {
    Say 'GPU build: torch from the cu126 index (CUDA 12.6).'
    Say 'Plain "pip install torch" on Windows gives a CPU-only build.'
} else {
    Say 'CPU build. Everything still works, roughly 3x slower per decision.'
}

# ---------------------------------------------------------------- 2. find uv or python
$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv) {
    Say 'using uv' 'Green'
} else {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) {
        Head 'FAILED: no uv and no python on PATH'
        Say 'Install uv:  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"'
        exit 1
    }
    Say 'uv not found, falling back to python -m venv + pip' 'Yellow'
}

$venvPy = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$isWindows = $true

function Run-Step($exe, $argList, $what) {
    Head $what
    & $exe @argList
    if ($LASTEXITCODE -ne 0) {
        Write-Host ''
        Write-Host "  FAILED: $what" -ForegroundColor Red
        exit 1
    }
}

# ---------------------------------------------------------------- 3. virtualenv
if (-not (Test-Path -LiteralPath $venvPy)) {
    if ($uv) { Run-Step 'uv' @('venv', '--python', $REQUIRED_PY, '.venv') "creating a Python $REQUIRED_PY environment" }
    else { Run-Step 'python' @('-m', 'venv', '.venv') 'creating a virtual environment' }
} else {
    Head 'reusing the existing .venv'
}

# ---------------------------------------------------------------- 4. torch
$torchAlready = & $venvPy -c "import torch,sys; print(torch.__version__)" 2>$null
if ($torchAlready) {
    Head "torch already installed: $torchAlready"
} elseif ($uv) {
    if ($Device -eq 'cuda') {
        Run-Step 'uv' @('pip', 'install', '--python', $venvPy, 'torch', '--index-url', $CUDA_INDEX) 'installing the GPU build of torch (this is a ~2.4 GB download)'
    } else {
        Run-Step 'uv' @('pip', 'install', '--python', $venvPy, 'torch') 'installing the CPU build of torch'
    }
} else {
    $base = 'https://download.pytorch.org/whl/cu126'
    if ($Device -eq 'cuda') { Run-Step $venvPy @('-m', 'pip', 'install', 'torch', '--index-url', $base) 'installing the GPU build of torch' }
    else { Run-Step $venvPy @('-m', 'pip', 'install', 'torch') 'installing the CPU build of torch' }
}

# ---------------------------------------------------------------- 5. the rest
if ($uv) { Run-Step 'uv' @('pip', 'install', '--python', $venvPy, '-r', 'requirements.lock.txt') 'installing the pinned dependencies' }
else { Run-Step $venvPy @('-m', 'pip', 'install', '-r', 'requirements.lock.txt') 'installing the pinned dependencies' }

# ---------------------------------------------------------------- 6. weights
if ($SkipWeights) {
    Head 'skipping the weight download (-SkipWeights)'
} else {
    Head 'downloading the model (~647 MB, once)'
    Say 'model:  convaiinnovations/laya-multilingual'
    Say 'page:   https://huggingface.co/convaiinnovations/laya-multilingual'
    Say 'into:   .data\huggingface   (deliberately not in git)'
    $env:HF_HOME = Join-Path $PSScriptRoot '.data\huggingface'
    $env:HF_HUB_DISABLE_SYMLINKS_WARNING = '1'
    $env:HF_HUB_DISABLE_PROGRESS_BARS = '0'
    & $venvPy -c @"
import os
os.environ['HF_HOME'] = r'$env:HF_HOME'
from huggingface_hub import snapshot_download

REPO = 'convaiinnovations/laya-multilingual'
print('  fetching', REPO)
path = snapshot_download(repo_id=REPO)
print('  downloaded to', path)
"@
    if ($LASTEXITCODE -ne 0) {
        Write-Host '  snapshot_download failed, trying through the laya loader instead' -ForegroundColor Yellow
        & $venvPy -c @"
import os
os.environ['HF_HOME'] = r'$env:HF_HOME'
import laya
a = laya.load('convaiinnovations/laya-multilingual', device='$Device')
print('  weights ready')
"@
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host '  FAILED: could not fetch the weights. Check your internet connection.' -ForegroundColor Red
        Write-Host '  You can also download them by hand from the link above and put the' -ForegroundColor Red
        Write-Host '  models--convaiinnovations--laya-multilingual folder under .data\huggingface\hub' -ForegroundColor Red
        exit 1
    }
}

# ---------------------------------------------------------------- 7. verify
Head 'verifying'
& $venvPy -c @"
import sys, torch, laya, gradio
print('  python  ', sys.version.split()[0])
print('  torch   ', torch.__version__)
print('  laya    ', laya.__version__)
print('  gradio  ', gradio.__version__)
print('  cuda    ', torch.cuda.is_available())
if torch.cuda.is_available():
    print('  gpu     ', torch.cuda.get_device_name(0))
    print('  arch    ', torch.cuda.get_arch_list()[:4], '...')
    free, total = torch.cuda.mem_get_info()
    print(f'  vram    {free/1024**2:.0f} / {total/1024**2:.0f} MB free')
"@
if ($LASTEXITCODE -ne 0) {
    Write-Host '  FAILED: the environment did not import cleanly' -ForegroundColor Red
    exit 1
}

Head 'done'
Say 'start the app with:   powershell -ExecutionPolicy Bypass -File start.ps1'
Say 'then open:            http://127.0.0.1:7860'
Write-Host ''
