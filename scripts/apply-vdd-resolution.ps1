# Apply DeskMirror vdd_settings.xml and restart Virtual Display Driver
#Requires -Version 5.1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SrcXml = Join-Path $ProjectRoot "resources\windows\vdd_settings.xml"
$DstDir = "C:\VirtualDisplayDriver"
$DstXml = Join-Path $DstDir "vdd_settings.xml"

if (-not (Test-Path $SrcXml)) {
    Write-Error "Missing $SrcXml"
}

if (-not (Test-Path $DstDir)) {
    New-Item -ItemType Directory -Path $DstDir -Force | Out-Null
}

Copy-Item -Path $SrcXml -Destination $DstXml -Force
Write-Host "[OK] Copied vdd_settings.xml -> $DstXml" -ForegroundColor Green
Write-Host ""
Write-Host "Note: VDD cannot expose 400x240 (driver minimum is 640x480)." -ForegroundColor Yellow
Write-Host "      Use 800x480 on the virtual monitor (same 5:3 as 3DS 400x240)." -ForegroundColor Yellow
Write-Host ""

$VddPackage = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Directory |
    Where-Object { $_.Name -like 'VirtualDrivers.Virtual-Display-Driver*' } |
    Select-Object -First 1

if ($VddPackage) {
    $DriverXml = Join-Path $VddPackage.FullName "SignedDrivers\x86\VDD\vdd_settings.xml"
    Copy-Item -Path $SrcXml -Destination $DriverXml -Force
    Write-Host "[OK] Updated driver package xml" -ForegroundColor Green
}

$VddControl = "$env:LOCALAPPDATA\Microsoft\WinGet\Links\VDD Control.exe"
if (Test-Path $VddControl) {
    Write-Host "Opening VDD Control — click 'Restart Driver' or toggle display off/on." -ForegroundColor Cyan
    Start-Process $VddControl
} else {
    Write-Host "Open VDD Control from Start menu and restart the driver." -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Then: Settings > Display > Virtual Display Driver > 800 x 480" -ForegroundColor Cyan
