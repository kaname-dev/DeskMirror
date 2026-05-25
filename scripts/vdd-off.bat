@echo off
setlocal
cd /d "%~dp0\.."

echo DeskMirror - Turn OFF virtual display
echo (Administrator approval required)
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Start-Process powershell -Verb RunAs -Wait -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File','\"%~dp0vdd-pnp.ps1\"','-Action','disable')"

if errorlevel 1 (
    echo [ERROR] Failed. Approve the UAC prompt and try again.
    pause
    exit /b 1
)

echo.
echo Done. Virtual display should be gone from Display Settings.
pause
exit /b 0
