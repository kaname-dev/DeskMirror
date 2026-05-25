# MSYS2 + devkitPro 3DS 開発環境のセットアップ（初回のみ）
$ErrorActionPreference = "Stop"

$MsysBash = "C:\msys64\usr\bin\bash.exe"
$SetupSh = (Join-Path $PSScriptRoot "setup-devkitpro.sh") -replace '\\', '/'

if (-not (Test-Path $MsysBash)) {
    Write-Host "MSYS2 をインストールしています (winget)..."
    winget install --id MSYS2.MSYS2 -e --accept-package-agreements --accept-source-agreements
}

if (-not (Test-Path $MsysBash)) {
    Write-Error "MSYS2 のインストールに失敗しました。"
}

Write-Host "==> devkitPro 3ds-dev ツールチェーンをインストール..."
& $MsysBash -lc "bash '$($SetupSh -replace '\\','/')'"

Write-Host "==> CIA 用 makerom / bannertool をインストール..."
& (Join-Path $PSScriptRoot "install-cia-tools.ps1")

$ToolsDst = "C:\msys64\opt\devkitpro\tools\bin"
if (Test-Path "C:\devkitPro\tools\bin") {
    New-Item -ItemType Directory -Force -Path $ToolsDst | Out-Null
    Copy-Item "C:\devkitPro\tools\bin\makerom.exe", "C:\devkitPro\tools\bin\bannertool.exe" $ToolsDst -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "セットアップ完了。"
Write-Host "ビルド例: .\scripts\build.ps1 -Target cia"
