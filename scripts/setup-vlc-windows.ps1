# One helper for VLC's HTTP interface on Windows. Run as Administrator.
# Defaults keep the network on Public and open only TCP 8080.

param(
    [string]$Password = "changeme",
    [int]$Port = 8080,
    [string]$Profile = "Public",
    [string]$VlcPath = "C:\Program Files\VideoLAN\VLC\vlc.exe",
    [switch]$BlockAllTcpExceptPort,
    [switch]$DisableVlcBlockRules,
    [switch]$SkipVlcRestart
)

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "NOT RUNNING AS ADMINISTRATOR. Right-click PowerShell -> 'Run as administrator'."
    exit 1
}

Write-Host "=== Network profile (unchanged: $Profile) ==="
Get-NetConnectionProfile | Select-Object InterfaceAlias, NetworkCategory | Format-Table -AutoSize

$profileObject = Get-NetFirewallProfile -Name $Profile
if ([string]$profileObject.AllowInboundRules -eq 'False' -or [string]$profileObject.AllowLocalFirewallRules -eq 'False') {
    Set-NetFirewallProfile -Name $Profile -AllowInboundRules True -AllowLocalFirewallRules True
    Write-Host "Enabled inbound/local firewall rules for the $Profile profile."
}

$allowName = "VLC Web Interface $Port"
Remove-NetFirewallRule -DisplayName $allowName -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName $allowName `
    -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow `
    -Profile $Profile -Enabled True | Out-Null

if ($DisableVlcBlockRules) {
    Get-NetFirewallRule | Where-Object {
        $_.DisplayName -match 'VLC' -and $_.Action -eq 'Block' -and $_.Direction -eq 'Inbound'
    } | Disable-NetFirewallRule
    Write-Host "Disabled inbound VLC Block rules."
}

if ($BlockAllTcpExceptPort) {
    $ruleName = "Block inbound TCP except $Port"
    $ranges = @()
    if ($Port -gt 1)     { $ranges += "1-$($Port - 1)" }
    if ($Port -lt 65535) { $ranges += "$($Port + 1)-65535" }
    Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName $ruleName `
        -Direction Inbound -Protocol TCP -LocalPort $ranges `
        -Action Block -Profile $Profile -Enabled True | Out-Null
    Write-Host "Blocking inbound TCP ports $($ranges -join ',') (port $Port stays open)."
}

if (-not $SkipVlcRestart) {
    Get-Process vlc -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 2
    if (-not (Test-Path $VlcPath)) {
        Write-Error "VLC not found at $VlcPath - pass -VlcPath with the correct path."
        exit 1
    }
    Start-Process -FilePath $VlcPath -ArgumentList @(
        "--extraintf=http", "--http-host=0.0.0.0", "--http-port=$Port", "--http-password=$Password"
    )
    Start-Sleep -Seconds 3
}

Write-Host "=== Firewall rules ==="
Get-NetFirewallRule | Where-Object DisplayName -match 'VLC' |
    Select-Object DisplayName, Enabled, Profile, Direction, Action | Format-Table -AutoSize
Write-Host "=== Listeners ==="
netstat -ano | findstr ":$Port"
Write-Host "Verify from the VM: curl -u :$Password http://<this-PC-IP>:$Port/requests/status.xml"
