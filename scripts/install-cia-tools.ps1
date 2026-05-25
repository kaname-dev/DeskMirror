# makerom / bannertool を %DEVKITPRO%\tools\bin に配置
$ErrorActionPreference = "Stop"

# MSYS2 + devkitPro ではツールは /opt/devkitpro (= C:\msys64\opt\devkitpro) に配置
$DevkitPro = if ($env:DEVKITPRO) { $env:DEVKITPRO } elseif (Test-Path "C:\msys64\opt\devkitpro") { "C:\msys64\opt\devkitpro" } else { "C:\devkitPro" }
$ToolsBin = Join-Path $DevkitPro "tools\bin"
$TempDir = Join-Path $env:TEMP "3ds-cia-tools"

New-Item -ItemType Directory -Force -Path $ToolsBin, $TempDir | Out-Null

function Get-LatestAssetUrl {
    param([string]$Repo, [string]$Pattern)
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest"
    $asset = $release.assets | Where-Object { $_.name -match $Pattern } | Select-Object -First 1
    if (-not $asset) { throw "No asset matching '$Pattern' in $Repo" }
    return $asset.browser_download_url, $asset.name
}

Write-Host "==> Downloading makerom (Project_CTR)..."
$makeromUrl, $makeromZip = Get-LatestAssetUrl -Repo "3DSGuy/Project_CTR" -Pattern "makerom.*win.*\.zip"
$makeromZipPath = Join-Path $TempDir $makeromZip
Invoke-WebRequest -Uri $makeromUrl -OutFile $makeromZipPath -UseBasicParsing
Expand-Archive -Path $makeromZipPath -DestinationPath (Join-Path $TempDir "makerom") -Force
$makeromExe = Get-ChildItem -Path (Join-Path $TempDir "makerom") -Filter "makerom.exe" -Recurse | Select-Object -First 1
if (-not $makeromExe) {
    # fallback: devkitPro buildtools layout
    $makeromExe = Get-ChildItem -Path (Join-Path $TempDir "makerom") -Filter "makerom*" -Recurse | Where-Object { $_.Extension -eq ".exe" } | Select-Object -First 1
}
if (-not $makeromExe) { throw "makerom.exe not found in archive" }
Copy-Item $makeromExe.FullName (Join-Path $ToolsBin "makerom.exe") -Force

Write-Host "==> Downloading bannertool..."
$bannertoolUrl, $bannertoolZip = Get-LatestAssetUrl -Repo "Epicpkmn11/bannertool" -Pattern "bannertool.*zip"
$bannertoolZipPath = Join-Path $TempDir $bannertoolZip
Invoke-WebRequest -Uri $bannertoolUrl -OutFile $bannertoolZipPath -UseBasicParsing
Expand-Archive -Path $bannertoolZipPath -DestinationPath (Join-Path $TempDir "bannertool") -Force
$bannertoolExe = Get-ChildItem -Path (Join-Path $TempDir "bannertool") -Filter "bannertool.exe" -Recurse | Select-Object -First 1
if (-not $bannertoolExe) { throw "bannertool.exe not found in archive" }
Copy-Item $bannertoolExe.FullName (Join-Path $ToolsBin "bannertool.exe") -Force

Write-Host "==> Done. Tools installed to: $ToolsBin"
Write-Host "    makerom.exe, bannertool.exe"
