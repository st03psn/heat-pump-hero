# HeatPump Hero — quick non-interactive update (PowerShell, Windows)
#
# Use this for fast iteration during testing from a Windows worktree to
# a HA config that's exposed via Samba (e.g. \\homeassistant\config) or
# a mounted drive. Copies packages, dashboard, blueprint, helper scripts.
#
# Recorder data is untouched, so reinstall / uninstall / reinstall keeps
# your sensor.hph_* history intact.
#
# Usage:
#   .\scripts\update.ps1 -HaConfig \\homeassistant\config
#   .\scripts\update.ps1 -HaConfig D:\hassio\config

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $HaConfig
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path -LiteralPath (Join-Path $HaConfig 'configuration.yaml'))) {
    throw "configuration.yaml not found under $HaConfig — wrong directory?"
}

Write-Host "==> HeatPump Hero update — target: $HaConfig"

function Ensure-Dir([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

# 1. Packages
Ensure-Dir (Join-Path $HaConfig 'packages')
Get-ChildItem -LiteralPath (Join-Path $repoRoot 'packages') -Filter '*.yaml' | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $HaConfig "packages\$($_.Name)") -Force
    Write-Host "    packages/$($_.Name)"
}

# 2. Dashboard YAML + assets
Ensure-Dir (Join-Path $HaConfig 'hph')
Copy-Item -LiteralPath (Join-Path $repoRoot 'dashboards\hph.yaml') `
          -Destination (Join-Path $HaConfig 'hph\dashboard.yaml') -Force
Write-Host "    hph/dashboard.yaml"

Ensure-Dir (Join-Path $HaConfig 'www\hph')
Copy-Item -LiteralPath (Join-Path $repoRoot 'dashboards\assets\*') `
          -Destination (Join-Path $HaConfig 'www\hph') -Recurse -Force
Write-Host "    www/hph/ (SVG assets)"

# 3. Blueprint
Ensure-Dir (Join-Path $HaConfig 'blueprints\script\hph')
Copy-Item -LiteralPath (Join-Path $repoRoot 'blueprints\hph_setup.yaml') `
          -Destination (Join-Path $HaConfig 'blueprints\script\hph\hph_setup.yaml') -Force
Write-Host "    blueprints/script/hph/hph_setup.yaml"

# 4. Helper scripts
Ensure-Dir (Join-Path $HaConfig 'scripts')
foreach ($f in @('export_heishahub.py', 'import_csv_to_ha_stats.py', 'analyze_heating_curve.py')) {
    $src = Join-Path $repoRoot "scripts\$f"
    if (Test-Path -LiteralPath $src) {
        Copy-Item -LiteralPath $src -Destination (Join-Path $HaConfig "scripts\$f") -Force
        Write-Host "    scripts/$f"
    }
}

# 5. configuration.yaml — add packages include if missing
$cfg = Join-Path $HaConfig 'configuration.yaml'
$cfgText = Get-Content -LiteralPath $cfg -Raw
if ($cfgText -notmatch 'packages:\s*!include_dir_named\s+packages') {
    if ($cfgText -match '(?m)^homeassistant:\s*$') {
        $newCfg = $cfgText -replace '(?m)^(homeassistant:\s*)$', "`$1`n  packages: !include_dir_named packages"
    } else {
        $newCfg = $cfgText.TrimEnd() + "`n`nhomeassistant:`n  packages: !include_dir_named packages`n"
    }
    Set-Content -LiteralPath $cfg -Value $newCfg -NoNewline
    Write-Host "    (added 'packages:' include to configuration.yaml)"
}

Write-Host ""
Write-Host "==> Update complete. In HA:"
Write-Host "  Developer Tools -> YAML -> Check Configuration  (must be green)"
Write-Host "  Developer Tools -> YAML -> All YAML configuration  (reload)"
Write-Host "    or"
Write-Host "  Settings -> System -> Restart Home Assistant  (if helpers / counters changed)"
