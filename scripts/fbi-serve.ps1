param(
    [Parameter(Position = 0)]
    [string]$DsIp,

    [switch]$WebUi,
    [switch]$Build,
    [switch]$KeepAlive,
    [switch]$OpenBrowser,
    [int]$Port = 8080,
    [int]$UiPort = 8765,
    [string]$HostIp = "",
    [string]$File = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PyScript = Join-Path $ScriptDir "fbi-serve.py"

$argsList = @()
if (Get-Command python -ErrorAction SilentlyContinue) {
    $argsList += "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $argsList += "py"
    $argsList += "-3"
} else {
    Write-Error "Python 3 is required. Install from https://www.python.org/downloads/"
}

$argsList += $PyScript

if ($WebUi -or -not $DsIp) {
    $argsList += "--webui"
} else {
    $argsList += $DsIp
}

if ($HostIp) { $argsList += "--host-ip"; $argsList += $HostIp }
$argsList += "--port"; $argsList += $Port
$argsList += "--ui-port"; $argsList += $UiPort
if ($Build) { $argsList += "--build" }
if ($KeepAlive) { $argsList += "--keep-alive" }
if ($OpenBrowser) { $argsList += "--open-browser" }
if ($File) { $argsList += "--file"; $argsList += $File }

& $argsList[0] $argsList[1..($argsList.Length - 1)]
exit $LASTEXITCODE
