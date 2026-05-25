# Enable or disable Virtual Display Driver (requires Administrator)
#Requires -Version 5.1
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("enable", "disable")]
    [string]$Action
)

$ErrorActionPreference = "Stop"

$device = Get-PnpDevice -Class Display -ErrorAction SilentlyContinue |
    Where-Object { $_.FriendlyName -eq "Virtual Display Driver" } |
    Select-Object -First 1

if (-not $device) {
    Write-Error "Virtual Display Driver not found in Device Manager."
    exit 1
}

if ($Action -eq "disable") {
    if ($device.Status -ne "OK") {
        Write-Host "[OK] Virtual Display Driver already disabled."
        exit 0
    }
    Write-Host "Disabling Virtual Display Driver..."
    Disable-PnpDevice -InstanceId $device.InstanceId -Confirm:$false
    Write-Host "[OK] Virtual display removed."
} else {
    if ($device.Status -eq "OK") {
        Write-Host "[OK] Virtual Display Driver already enabled."
        exit 0
    }
    Write-Host "Enabling Virtual Display Driver..."
    Enable-PnpDevice -InstanceId $device.InstanceId -Confirm:$false
    Write-Host "[OK] Virtual Display Driver enabled (monitors follow vdd_settings.xml)."
}

exit 0
