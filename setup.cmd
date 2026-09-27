@echo off
REM One-time setup. Creates the virtualenv and installs the pinned environment.
REM Idempotent: safe to run again if something is missing.
setlocal
set REPO=%~dp0
cd /d "%REPO%"

echo.
echo   ============================================================
echo    Laya - setup
echo   ============================================================
echo.

where uv >nul 2>&1
if errorlevel 1 (
    echo   ERROR: uv not found. Install it with:  powershell -c "irm https://astral.sh/uv/install.ps1 ^| iex"
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo   Creating Python 3.12 virtualenv...
    uv venv --python 3.12 .venv
    if errorlevel 1 goto :fail
)

REM The GPU torch must be installed from the cu126 index, not PyPI.
REM PyPI ships a CPU-only Windows wheel; cu126 is the last index that still
REM supports this machine's Pascal card. See requirements.lock.txt.
echo   Installing torch for this GPU...
uv pip install --python .venv\Scripts\python.exe torch --index-url https://download.pytorch.org/whl/cu126
if errorlevel 1 goto :fail

echo   Installing the rest from the lockfile...
uv pip install --python .venv\Scripts\python.exe -r requirements.lock.txt
if errorlevel 1 goto :fail

echo.
echo   Verifying...
.venv\Scripts\python.exe -c "import torch, laya, gradio; print('  torch', torch.__version__); print('  laya', laya.__version__); print('  gradio', gradio.__version__); print('  cuda', torch.cuda.is_available()); print('  arch', torch.cuda.get_arch_list() if torch.cuda.is_available() else 'n/a')"
if errorlevel 1 goto :fail

echo.
echo   First run will download ~650 MB of weights into .data\huggingface
echo   and then everything works offline.
echo.
echo   Done. Start the app with:   powershell -ExecutionPolicy Bypass -File start.ps1
echo.
pause
exit /b 0

:fail
echo.
echo   Setup failed. Read the message above.
echo.
pause
exit /b 1
