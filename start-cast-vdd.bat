@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo  DeskMirror - Virtual Monitor Cast
echo ========================================
echo.

if "%~1"=="" (
    echo Usage: start-cast-vdd.bat ^<3DS IP^>
    echo.
    echo Requires a virtual display in Windows ^(see scripts\setup-virtual-monitor.ps1^)
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

%PY% "%~dp0scripts\pc-cast.py" --host %1 --vdd %*
set EXITCODE=%ERRORLEVEL%

:end
echo.
pause
endlocal
exit /b %EXITCODE%
