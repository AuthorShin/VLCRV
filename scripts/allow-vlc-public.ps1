# Run as Administrator on the VLC PC. Keeps the network profile PUBLIC and
# only allows inbound TCP 8080 for VLC's HTTP interface.

param(
    [string]$Password = "changeme",
    [int]$Port = 8080,
    [string]$VlcPath = "C:\Program Files\VideoLAN\VLC\vlc.exe",
    [switch]$SkipVlcRestart
)

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "NOT RUNNING AS ADMINISTRATOR. Right-click PowerShell -> 'Run as administrator' and try again."
    exit 1
}

Write-Host "=== 1. Network profile (stays Public) ==="
Get-NetConnectionProfile | Select-Object InterfaceAlias, NetworkCategory | Format-Table -AutoSize

Write-Host "=== 2. Make sure Public profile honours inbound rules ==="
$publicProfile = Get-NetFirewallProfile -Name Public
$publicProfile | Select-Object Name, Enabled, DefaultInboundAction, AllowInboundRules, AllowLocalFirewallRules | Format-List
if (-not $publicProfile.AllowInboundRules -or -not $publicProfile.AllowLocalFirewallRules) {
    Set-NetFirewallProfile -Name Public -AllowInboundRules True -AllowLocalFirewallRules True
    Write-Host "Enabled inbound/local rules for the Public profile."
}

Write-Host "=== 3. Recreate inbound rule for PUBLIC only ==="
Remove-NetFirewallRule -DisplayName "VLC Web Interface $Port" -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "VLC Web Interface $Port" `
    -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow `
    -Profile Public -Enabled True | Out-Null
Get-NetFirewallRule -DisplayName "VLC Web Interface $Port" |
    Select-Object DisplayName, Enabled, Profile, Direction, Action | Format-Table -AutoSize

if (-not $SkipVlcRestart) {
    Write-Host "=== 4. Restarting VLC bound to 0.0.0.0 ==="
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
}

Write-Host "=== 5. Listeners ==="
netstat -ano | findstr ":$Port"
Write-Host ""
Write-Host "Expected: TCP 0.0.0.0:$Port LISTENING and rule Enabled=True Profile=Public"
Write-Host "Verify from the VM: curl -u :$Password http://<this-PC-IP>:$Port/requests/status.xml"
