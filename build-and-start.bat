@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo  3DS FBI Remote Install - Build + Web UI
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python 3 が見つかりません。
        set EXITCODE=1
        goto :end
    )
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\fbi-serve.ps1" -WebUi -Build %*
set EXITCODE=%ERRORLEVEL%

if not %EXITCODE%==0 (
    echo.
    echo [ERROR] 起動に失敗しました (code %EXITCODE%)
)

:end
echo.
pause
endlocal
if not defined EXITCODE set EXITCODE=0
exit /b %EXITCODE%
