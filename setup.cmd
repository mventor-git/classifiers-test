@echo off
REM Thin wrapper kept for people who double-click.
REM The real installer is installer.ps1, which handles both models and is
REM idempotent. This just calls it so there is one implementation.
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0\installer.ps1" %*
set RC=%ERRORLEVEL%
if not "%RC%"=="0" (
    echo.
    echo   Setup did not finish. See the message above.
    echo.
)
exit /b %RC%
