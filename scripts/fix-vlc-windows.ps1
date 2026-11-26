# Run this in PowerShell **as Administrator** on the PC that plays VLC.
# It makes VLC's HTTP interface reachable from other devices on the LAN.

param(
    [string]$Password = "changeme",
    [int]$Port = 8080,
    [string]$VlcPath = "C:\Program Files\VideoLAN\VLC\vlc.exe"
)

Write-Host "=== 1. Network profiles (must be Private for the firewall rule) ==="
Get-NetConnectionProfile | Select-Object InterfaceAlias, NetworkCategory | Format-Table -AutoSize

Write-Host "=== 2. Current listeners on port $Port ==="
netstat -ano | findstr ":$Port"

Write-Host "=== 3. Opening inbound TCP $Port for ALL profiles ==="
$rule = Get-NetFirewallRule -DisplayName "VLC Web Interface $Port" -ErrorAction SilentlyContinue
if (-not $rule) {
    New-NetFirewallRule -DisplayName "VLC Web Interface $Port" `
        -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow -Profile Any | Out-Null
} else {
    Set-NetFirewallRule -DisplayName "VLC Web Interface $Port" -Profile Any -Enabled True | Out-Null
}

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
Write-Host "Expected: TCP 0.0.0.0:$Port LISTENING"
Write-Host "Then test from the VM/phone: http://<this-PC-IP>:$Port/requests/status.xml"
Write-Host "Make sure the container's VLC_HTTP_PASSWORD is '$Password'."
