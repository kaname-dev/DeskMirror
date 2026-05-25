@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo  DeskMirror - Cast
echo ========================================
echo.

set CONFIG=%~dp0cast-config.json
set EXAMPLE=%~dp0cast-config.json.example

if not exist "%CONFIG%" (
    echo [INFO] cast-config.json not found.
    if exist "%EXAMPLE%" (
        echo        Copying from cast-config.json.example ...
        echo        Edit "host" to your 3DS IP, then save and run again.
        copy /Y "%EXAMPLE%" "%CONFIG%" >nul
        echo.
        echo 3DS IP is shown on the bottom screen when DeskMirror is running.
        echo.
        notepad "%CONFIG%"
    ) else (
        echo [ERROR] cast-config.json.example not found.
        set EXITCODE=1
        goto end
    )
)

where python >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python 3 not found.
        set EXITCODE=1
        goto end
    )
    set PY=py -3
) else (
    set PY=python
)

echo Config: %CONFIG%
echo Stop: Ctrl+C
echo.

if "%~1"=="" (
    %PY% "%~dp0scripts\pc-cast.py"
) else (
    echo Override 3DS IP: %~1
    %PY% "%~dp0scripts\pc-cast.py" --host %1 %*
)
set EXITCODE=%ERRORLEVEL%

:end
echo.
if not "%EXITCODE%"=="0" (
    echo [ERROR] Exit code %EXITCODE%
    echo Try: pip install -r scripts\requirements-cast.txt
)
pause
endlocal
if not defined EXITCODE set EXITCODE=0
exit /b %EXITCODE%
