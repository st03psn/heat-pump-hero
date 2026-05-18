# HeatPump Hero — dev debug loop
#
# Deploys, reloads HPH via REST API, waits, then prints entity states + errors.
# Replaces the manual deploy → HA UI reload → manual check cycle.
#
# Usage:
#   .\scripts\debug_hph.ps1                  # deploy + reload + status
#   .\scripts\debug_hph.ps1 -SkipDeploy      # reload + status only (already deployed)
#   .\scripts\debug_hph.ps1 -StatusOnly      # just print current status, no deploy/reload

[CmdletBinding()]
param(
    [switch] $SkipDeploy,
    [switch] $StatusOnly
)

$ErrorActionPreference = 'Stop'

$HA_URL   = "http://192.168.111.73:8123"
$HA_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIyOWM3ZDllM2ZjMzc0ZGQ0YmIxNmY0N2VmYjliODYyNCIsImlhdCI6MTc3OTEwNDU1NiwiZXhwIjoyMDk0NDY0NTU2fQ.8cHz_EXmWYmtjhmFtx5LdndM6ZioaXbNgWhHaTQM-GU"
$h        = @{ Authorization = "Bearer $HA_TOKEN"; "Content-Type" = "application/json" }

# ── 1. Deploy ────────────────────────────────────────────────────────────────
if (-not $StatusOnly -and -not $SkipDeploy) {
    & "$PSScriptRoot\deploy_dev.ps1"
}

# ── 2. Reload HPH ────────────────────────────────────────────────────────────
if (-not $StatusOnly) {
    $entries = Invoke-RestMethod "$HA_URL/api/config/config_entries/entry" -Headers $h
    $hph = $entries | Where-Object { $_.domain -eq "hph" } | Select-Object -First 1
    if (-not $hph) { throw "No 'hph' config entry found — is HPH installed?" }
    Invoke-RestMethod "$HA_URL/api/config/config_entries/entry/$($hph.entry_id)/reload" -Method POST -Headers $h | Out-Null
    Write-Host "==> HPH reloaded (entry $($hph.entry_id))"
    Write-Host "    Waiting 5 s for platform setup..."
    Start-Sleep -Seconds 5
}

# ── 3. Fetch current states ──────────────────────────────────────────────────
$states = Invoke-RestMethod "$HA_URL/api/states" -Headers $h
$hphStates = $states | Where-Object { $_.entity_id -match "^(switch|select|number|text|button|sensor|binary_sensor)\.hph_" }

# Unavailable / unknown first
$bad = $hphStates | Where-Object { $_.state -in @("unavailable","unknown") } | Sort-Object entity_id
$ok  = $hphStates | Where-Object { $_.state -notin @("unavailable","unknown") } | Sort-Object entity_id

Write-Host ""
if ($bad.Count -gt 0) {
    Write-Host "=== UNAVAILABLE / UNKNOWN ($($bad.Count)) ==="
    $bad | ForEach-Object { "  {0,-60} {1}" -f $_.entity_id, $_.state }
} else {
    Write-Host "=== All HPH entities are available ($($ok.Count) total) ==="
}

Write-Host ""
Write-Host "=== switch.hph_* ==="
# Build lookup to avoid $_ scoping conflicts inside nested Where-Object
$lookup = @{}; $states | ForEach-Object { $lookup[$_.entity_id] = $_.state }
$hphStates | Where-Object { $_.entity_id -match "^switch\.hph_" } | Sort-Object entity_id | ForEach-Object {
    "  {0,-55} {1}" -f $_.entity_id, $_.state
}

# ── 4. Recent HPH errors from log ────────────────────────────────────────────
Write-Host ""
Write-Host "=== Recent HPH log entries (last 30 lines matching 'hph') ==="
$logPath = "P:\home-assistant.log"
if (Test-Path $logPath) {
    Get-Content $logPath | Where-Object { $_ -match "\bhph\b|HeatPump Hero" } | Select-Object -Last 30 | ForEach-Object { "  $_" }
} else {
    Write-Host "  (log not accessible at $logPath — check Samba mount)"
}

exit 0
