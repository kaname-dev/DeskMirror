@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo  DeskMirror - FBI Web UI
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python 3 not found.
        echo Install from https://www.python.org/downloads/
        set EXITCODE=1
        goto end
    )
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\fbi-serve.ps1" -WebUi %*
set EXITCODE=%ERRORLEVEL%

if not %EXITCODE%==0 (
    echo.
    echo [ERROR] Server failed to start (exit code %EXITCODE%)
)

:end
echo.
pause
endlocal
if not defined EXITCODE set EXITCODE=0
exit /b %EXITCODE%
