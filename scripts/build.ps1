param(
    [ValidateSet("all", "3dsx", "cia", "clean")]
    [string]$Target = "cia"
)

$MsysBash = "C:\msys64\usr\bin\bash.exe"
if (-not (Test-Path $MsysBash)) {
    Write-Error "MSYS2 not found. Run scripts\setup-devkitpro.ps1 first."
    exit 1
}

$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Drive = $ProjectDir.Substring(0, 1).ToLower()
$Rest = $ProjectDir.Substring(2) -replace '\\', '/'
$ProjectDirMsys = "/$Drive$Rest"

$bashCmd = "source /etc/profile.d/devkit-env.sh && cd '$ProjectDirMsys' && make $Target"
& $MsysBash -lc $bashCmd
exit $LASTEXITCODE
