@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo  DeskMirror - Sender
echo ========================================
echo.

if "%~1"=="" (
    echo Usage: start-cast.bat ^<3DS IP^>
    echo Example: start-cast.bat 192.168.1.42
    echo.
    echo 3DS IP is shown on the bottom screen when the app is running.
    set EXITCODE=1
    goto :end
)

where python >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python 3 not found.
        set EXITCODE=1
        goto :end
    )
    set PY=py -3
) else (
    set PY=python
)

%PY% "%~dp0scripts\pc-cast.py" --host %1 %*
set EXITCODE=%ERRORLEVEL%

:end
echo.
pause
endlocal
exit /b %EXITCODE%
