# Run as Administrator on the VLC PC. Keeps the Public profile but blocks all
# inbound TCP ports EXCEPT the one used by VLC's HTTP interface (default 8080).
# The existing "VLC Web Interface 8080" allow rule still works because its port
# is deliberately not part of this block rule.

param(
    [int]$Port = 8080,
    [string]$Profile = "Public"
)

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "NOT RUNNING AS ADMINISTRATOR. Right-click PowerShell -> 'Run as administrator'."
    exit 1
}

$ruleName = "Block inbound TCP except $Port"
Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

$blockedRanges = @()
if ($Port -gt 1)        { $blockedRanges += "1-$($Port - 1)" }
if ($Port -lt 65535)    { $blockedRanges += "$($Port + 1)-65535" }

New-NetFirewallRule -DisplayName $ruleName `
    -Direction Inbound -Protocol TCP -LocalPort $blockedRanges `
    -Action Block -Profile $Profile -Enabled True | Out-Null

Write-Host "=== Rule ==="
Get-NetFirewallRule -DisplayName $ruleName |
    Select-Object DisplayName, Enabled, Profile, Direction, Action | Format-Table -AutoSize

Write-Host "=== Blocked port ranges (8080 intentionally absent) ==="
Get-NetFirewallRule -DisplayName $ruleName | Get-NetFirewallPortFilter |
    Select-Object -ExpandProperty LocalPort

Write-Host ""
Write-Host "Allow rule must still be enabled:"
Get-NetFirewallRule -DisplayName "VLC Web Interface $Port" -ErrorAction SilentlyContinue |
    Select-Object DisplayName, Enabled, Profile, Direction, Action | Format-Table -AutoSize
Write-Host "Verify from the VM: curl -u :changeme http://<this-PC-IP>:$Port/requests/status.xml"
