# Run this in PowerShell **as Administrator** on the PC that plays VLC.
# It makes VLC's HTTP interface reachable from other devices on the LAN.

param(
    [string]$Password = "changeme",
    [int]$Port = 8080,
    [string]$VlcPath = "C:\Program Files\VideoLAN\VLC\vlc.exe",
    [switch]$SkipProfileChange
)

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "NOT RUNNING AS ADMINISTRATOR. Right-click PowerShell -> 'Run as administrator' and try again."
    exit 1
}

Write-Host "=== 1. Network profiles ==="
Get-NetConnectionProfile | Select-Object InterfaceAlias, NetworkCategory | Format-Table -AutoSize

if (-not $SkipProfileChange) {
    Write-Host "=== 2. Setting active network profiles to Private ==="
    Get-NetConnectionProfile | ForEach-Object {
        if ($_.NetworkCategory -ne 'Private') {
            Set-NetConnectionProfile -InterfaceAlias $_.InterfaceAlias -NetworkCategory Private
        }
    }
}

Write-Host "=== 3. Recreating inbound firewall rule for ALL profiles ==="
Remove-NetFirewallRule -DisplayName "VLC Web Interface $Port" -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "VLC Web Interface $Port" `
    -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow `
    -Profile Any -Enabled True | Out-Null
Get-NetFirewallRule -DisplayName "VLC Web Interface $Port" |
    Select-Object DisplayName, Enabled, Profile, Direction, Action | Format-Table -AutoSize

Write-Host "=== 4. Restarting VLC with explicit host/port/password ==="
Get-Process vlc -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
if (-not (Test-Path $VlcPath)) {
    Write-Error "VLC not found at $VlcPath - pass -VlcPath with the correct path."
    exit 1
}
Start-Process -FilePath $VlcPath -ArgumentList @(
    "--extraintf=http",
    "--http-host=0.0.0.0",
    "--http-port=$Port",
    "--http-password=$Password"
)

Start-Sleep -Seconds 3
Write-Host "=== 5. Listeners after restart ==="
netstat -ano | findstr ":$Port"
Write-Host ""
Write-Host "Expected: TCP 0.0.0.0:$Port LISTENING and rule Enabled=True Profile=Any"
Write-Host "Test from the VM/phone: http://<this-PC-IP>:$Port/requests/status.xml"
