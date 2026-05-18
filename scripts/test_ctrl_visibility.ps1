# HeatPump Hero — Control facade visibility test
#
# Checks every CTRL_FACADES proxy entity:
#   1. Is the writer helper populated (non-empty)?
#   2. Does the target entity exist in HA?
#   3. Is the proxy entity available (not unavailable/unknown)?
#   4. Which conditional cards in the Control tab would hide/show it?
#
# Usage:
#   .\scripts\test_ctrl_visibility.ps1
#   .\scripts\test_ctrl_visibility.ps1 -Verbose   # include OK entities too

[CmdletBinding()]
param([switch] $ShowOk)

$HA_URL   = if ($env:HA_URL)   { $env:HA_URL }   else { "http://homeassistant.local:8123" }
$HA_TOKEN = if ($env:HA_TOKEN) { $env:HA_TOKEN } else {
    Write-Error "Set `$env:HA_TOKEN to a long-lived access token before running this script."
    exit 1
}
$h = @{ Authorization = "Bearer $HA_TOKEN"; "Content-Type" = "application/json" }

# ── 1. Fetch all states ───────────────────────────────────────────────────────
$states  = Invoke-RestMethod "$HA_URL/api/states" -Headers $h
$lookup  = @{}; $states | ForEach-Object { $lookup[$_.entity_id] = $_.state }

# ── 2. CTRL_FACADES map: proxy -> writer ─────────────────────────────────────
# Derived from const.py CTRL_FACADES (kept in sync manually or via test run)
$facades = [ordered]@{
    # select proxies
    "select.hph_ctrl_operating_mode"   = "text.hph_ctrl_write_operating_mode"
    "select.hph_quiet_mode"            = "text.hph_ctrl_write_quiet_mode"
    "select.hph_active_zones"          = "text.hph_ctrl_write_active_zones"
    "select.hph_bivalent_mode"         = "text.hph_ctrl_write_bivalent_mode"
    "select.hph_heating_control"       = "text.hph_ctrl_write_heating_control"
    "select.hph_dhw_sensor_selection"  = "text.hph_ctrl_write_dhw_sensor_selection"
    "select.hph_powerful_mode"         = "text.hph_ctrl_write_powerful_mode"
    "select.hph_smart_dhw"             = "text.hph_ctrl_write_smart_dhw"
    # switch proxies
    "switch.hph_power"                 = "text.hph_ctrl_write_power"
    "switch.hph_holiday"               = "text.hph_ctrl_write_holiday"
    "switch.hph_force_defrost"         = "text.hph_ctrl_write_force_defrost"
    # number proxies
    "number.hph_z1_heat_shift"         = "text.hph_ctrl_write_z1_heat_shift"
    "number.hph_z1_curve_high"         = "text.hph_ctrl_write_z1_curve_high"
    "number.hph_z1_curve_low"          = "text.hph_ctrl_write_z1_curve_low"
    "number.hph_z1_outside_high"       = "text.hph_ctrl_write_z1_outside_high"
    "number.hph_z1_outside_low"        = "text.hph_ctrl_write_z1_outside_low"
    "number.hph_z2_heat_shift"         = "text.hph_ctrl_write_z2_heat_shift"
    "number.hph_z2_curve_high"         = "text.hph_ctrl_write_z2_curve_high"
    "number.hph_z2_curve_low"          = "text.hph_ctrl_write_z2_curve_low"
    "number.hph_z2_outside_high"       = "text.hph_ctrl_write_z2_outside_high"
    "number.hph_z2_outside_low"        = "text.hph_ctrl_write_z2_outside_low"
    "number.hph_dhw_target"            = "text.hph_ctrl_write_dhw_target"
    "number.hph_dhw_heat_delta"        = "text.hph_ctrl_write_dhw_heat_delta"
    "number.hph_heating_cutoff"        = "text.hph_ctrl_write_heating_cutoff"
    "number.hph_room_heat_delta"       = "text.hph_ctrl_write_room_heat_delta"
    "number.hph_max_pump_duty"         = "text.hph_ctrl_write_max_pump_duty"
    "number.hph_cool_delta"            = "text.hph_ctrl_write_cool_delta"
    "number.hph_bivalent_start_temp"   = "text.hph_ctrl_write_bivalent_start_temp"
    "number.hph_heater_delay_time"     = "text.hph_ctrl_write_heater_delay_time"
    "number.hph_heater_start_delta"    = "text.hph_ctrl_write_heater_start_delta"
    "number.hph_heater_stop_delta"     = "text.hph_ctrl_write_heater_stop_delta"
    # button proxies
    "button.hph_force_dhw"             = "text.hph_ctrl_write_force_dhw"
}

# ── 3. Evaluate each proxy ────────────────────────────────────────────────────
$bad = @(); $ok = @()

foreach ($proxy in $facades.Keys) {
    $writer      = $facades[$proxy]
    $writerVal   = $lookup[$writer]            # entity-ID stored in text helper
    $proxyState  = $lookup[$proxy] ?? "NOT_IN_HA"
    $targetState = if ($writerVal) { $lookup[$writerVal] ?? "NOT_IN_HA" } else { $null }

    $issues = @()
    if ($proxyState -eq "NOT_IN_HA")           { $issues += "proxy missing" }
    if (-not $writerVal)                        { $issues += "writer empty (vendor-specific, correctly hidden)" }
    elseif ($targetState -eq "NOT_IN_HA")      { $issues += "target '$writerVal' not in HA" }
    elseif ($targetState -in @("unavailable","unknown")) { $issues += "target state=$targetState" }

    if ($proxyState -in @("unavailable","unknown","NOT_IN_HA")) {
        $bad += [PSCustomObject]@{ Proxy=$proxy; Writer=$writer; WriterVal=$writerVal; ProxyState=$proxyState; Issues=($issues -join "; ") }
    } else {
        $ok  += [PSCustomObject]@{ Proxy=$proxy; State=$proxyState; WriterVal=$writerVal }
    }
}

# ── 4. Report ─────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== CTRL_FACADES: available (should be VISIBLE in dashboard) ===" -ForegroundColor Green
$ok | ForEach-Object { "  [OK] {0,-42} = {1}" -f $_.Proxy, $_.State }

Write-Host ""
Write-Host "=== CTRL_FACADES: unavailable/missing ===" -ForegroundColor Yellow

# Split: empty writer (expected) vs. real problems
$expectedHidden = $bad | Where-Object { -not $_.WriterVal }
$broken         = $bad | Where-Object { $_.WriterVal }

if ($broken) {
    Write-Host "  --- BROKEN (writer set but proxy unavailable) ---" -ForegroundColor Red
    $broken | ForEach-Object {
        "  [BAD] {0,-42}  writer->{1}  target-state:{2}  ({3})" -f $_.Proxy, $_.WriterVal, ($lookup[$_.WriterVal] ?? "?"), $_.Issues
    }
}
if ($expectedHidden) {
    Write-Host "  --- Expected hidden (writer empty = vendor feature not present) ---" -ForegroundColor DarkGray
    $expectedHidden | ForEach-Object {
        "  [ - ] {0,-42}  (writer '{1}' is empty)" -f $_.Proxy, $_.Writer
    }
}

Write-Host ""
Write-Host "Summary: $($ok.Count) available, $($broken.Count) broken, $($expectedHidden.Count) expected-hidden" -ForegroundColor Cyan
