@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo  3DS FBI Remote Install - Web UI
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python 3 が見つかりません。
        echo https://www.python.org/downloads/ からインストールしてください。
        set EXITCODE=1
        goto :end
    )
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\fbi-serve.ps1" -WebUi %*
set EXITCODE=%ERRORLEVEL%

if not %EXITCODE%==0 (
    echo.
    echo [ERROR] サーバー起動に失敗しました (code %EXITCODE%)
)

:end
echo.
pause
endlocal
if not defined EXITCODE set EXITCODE=0
exit /b %EXITCODE%
