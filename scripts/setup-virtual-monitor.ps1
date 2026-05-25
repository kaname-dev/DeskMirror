# DeskMirror: add a Windows virtual monitor for 3DS extended desktop
#Requires -Version 5.1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$OptionSrc = Join-Path $ProjectRoot "resources\windows\DeskMirror-option.txt"
$OptionDst = "C:\IddSampleDriver\option.txt"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " DeskMirror - Virtual Monitor Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Windows cannot use 3DS as a real HDMI monitor."
Write-Host "Install a virtual display driver, then stream that display to 3DS."
Write-Host ""

# Copy recommended resolution preset
if (-not (Test-Path "C:\IddSampleDriver")) {
    New-Item -ItemType Directory -Path "C:\IddSampleDriver" -Force | Out-Null
}
Copy-Item -Path $OptionSrc -Destination $OptionDst -Force
Write-Host "[OK] Copied option preset to $OptionDst (400x240 = 3DS top screen)" -ForegroundColor Green

Write-Host ""
Write-Host "Step 1: Install Virtual Display Driver" -ForegroundColor Yellow
Write-Host "  winget install --id VirtualDrivers.Virtual-Display-Driver -e"
Write-Host "  Or download: https://github.com/VirtualDrivers/Virtual-Display-Driver/releases"
Write-Host ""
Write-Host "Step 2: In Windows Settings > Display" -ForegroundColor Yellow
Write-Host "  - Set 'Extend these displays'"
Write-Host "  - Drag the virtual monitor beside your main display"
Write-Host "  - Resolution: 400x240 on the virtual monitor (3DS native)"
Write-Host ""
Write-Host "Step 3: Start DeskMirror on 3DS, then on PC:" -ForegroundColor Yellow
Write-Host "  start-cast-vdd.bat <3DS IP>"
Write-Host ""

$install = Read-Host "Try winget install now? (y/N)"
if ($install -match '^[yY]') {
    try {
        winget install --id VirtualDrivers.Virtual-Display-Driver -e --accept-package-agreements --accept-source-agreements
        Write-Host "[OK] winget finished. Open VDC app to enable the virtual monitor." -ForegroundColor Green
    } catch {
        Write-Host "[WARN] winget failed. Install manually from GitHub releases." -ForegroundColor Yellow
        Write-Host $_.Exception.Message
    }
}

Write-Host ""
Write-Host "List monitors: python scripts\pc-cast.py --list-monitors" -ForegroundColor Cyan
