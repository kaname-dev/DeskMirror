# Self-elevate then run vdd-pnp.ps1 (used from Python / cast)
#Requires -Version 5.1
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("enable", "disable")]
    [string]$Action
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$target = Join-Path $scriptDir "vdd-pnp.ps1"

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if ($isAdmin) {
    & $target -Action $Action
    exit $LASTEXITCODE
}

$argList = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$target`"",
    "-Action", $Action
)
$proc = Start-Process -FilePath "powershell.exe" -Verb RunAs -Wait -PassThru -ArgumentList $argList
exit $proc.ExitCode
