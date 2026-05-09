# HeatPump Hero — CLI uninstaller (PowerShell, Windows)
#
# Removes every file the installer ever wrote into a HA config directory.
# Does NOT touch:
#   - HA's recorder DB (sensor.hph_* history stays intact until the
#     configured retention window expires)
#   - Long-Term Statistics
#   - HACS integrations or frontend cards
#   - User exports under www/heishahub_exports
#
# The 'packages: !include_dir_named packages' line in configuration.yaml
# is removed only if the packages/ directory is left empty afterwards.
#
# Idempotent. Run repeatedly without harm.
#
# Usage:
#   .\scripts\uninstall.ps1 -HaConfig \\homeassistant\config
#   .\scripts\uninstall.ps1 -HaConfig D:\hassio\config -DryRun
#   .\scripts\uninstall.ps1 -HaConfig D:\hassio\config -Yes

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $HaConfig,
    [switch] $DryRun,
    [switch] $Yes
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath (Join-Path $HaConfig 'configuration.yaml'))) {
    throw "configuration.yaml not found under $HaConfig — wrong directory?"
}

Write-Host "==> HeatPump Hero uninstaller"
Write-Host "    Target: $HaConfig"
if ($DryRun) { Write-Host "    Mode:   DRY RUN (no changes)" }

$targets = New-Object System.Collections.Generic.List[string]

# 1. Packages — every hph_*.yaml in /config/packages/
$pkgDir = Join-Path $HaConfig 'packages'
if (Test-Path -LiteralPath $pkgDir) {
    Get-ChildItem -LiteralPath $pkgDir -Filter 'hph_*.yaml' -File -ErrorAction SilentlyContinue |
        ForEach-Object { $targets.Add($_.FullName) }
}

# 2. Dashboard YAML + dir
$dashYaml = Join-Path $HaConfig 'hph\dashboard.yaml'
$dashDir  = Join-Path $HaConfig 'hph'
if (Test-Path -LiteralPath $dashYaml) { $targets.Add($dashYaml) }
if (Test-Path -LiteralPath $dashDir)  { $targets.Add($dashDir) }

# 3. Dashboard SVG / asset dir
$assets = Join-Path $HaConfig 'www\hph'
if (Test-Path -LiteralPath $assets) { $targets.Add($assets) }

# 4. Setup blueprint
$bpYaml = Join-Path $HaConfig 'blueprints\script\hph\hph_setup.yaml'
$bpDir  = Join-Path $HaConfig 'blueprints\script\hph'
if (Test-Path -LiteralPath $bpYaml) { $targets.Add($bpYaml) }
if (Test-Path -LiteralPath $bpDir)  { $targets.Add($bpDir) }

# 5. Helper Python scripts
foreach ($f in @('export_heishahub.py', 'import_csv_to_ha_stats.py', 'analyze_heating_curve.py')) {
    $p = Join-Path $HaConfig "scripts\$f"
    if (Test-Path -LiteralPath $p) { $targets.Add($p) }
}

# 6. NOT touched (just informational)
$exportDir = Join-Path $HaConfig 'www\heishahub_exports'

if ($targets.Count -eq 0) {
    Write-Host "==> Nothing to remove. HeatPump Hero is not installed in this config dir."
    return
}

Write-Host ""
Write-Host "==> Files / directories that will be removed:"
foreach ($t in $targets) { Write-Host "    $t" }

if (Test-Path -LiteralPath $exportDir) {
    Write-Host ""
    Write-Host "==> Note: user data NOT touched:"
    Write-Host "    $exportDir  (your CSV / JSON / XLSX exports — delete manually if wanted)"
}

Write-Host ""
Write-Host "==> NOT touched (by design):"
Write-Host "    Recorder DB / Long-Term Statistics — sensor.hph_* history stays"
Write-Host "    intact and naturally drops once the recorder retention window expires."
Write-Host "    HACS integrations and frontend cards — manage via HACS."

if ($DryRun) {
    Write-Host ""
    Write-Host "==> DRY RUN — exiting without changes."
    return
}

if (-not $Yes) {
    Write-Host ""
    $confirm = Read-Host "Proceed? [y/N]"
    if ($confirm -notmatch '^(y|yes)$') {
        Write-Host "Aborted."
        return
    }
}

Write-Host "==> Removing"
# Sort by path length descending so children come before parents (so dirs
# are empty by the time we try to remove them).
$sorted = $targets | Sort-Object -Property Length -Descending
foreach ($t in $sorted) {
    if (Test-Path -LiteralPath $t -PathType Leaf) {
        Remove-Item -LiteralPath $t -Force
        Write-Host "    removed file: $t"
    }
    elseif (Test-Path -LiteralPath $t -PathType Container) {
        $contents = Get-ChildItem -LiteralPath $t -Force -ErrorAction SilentlyContinue
        if (-not $contents) {
            Remove-Item -LiteralPath $t -Force
            Write-Host "    removed dir:  $t"
        } else {
            Write-Host "    kept dir:     $t  (not empty — contains user files)"
        }
    }
}

# 7. Drop 'packages:' include if /config/packages/ is now empty
if (Test-Path -LiteralPath $pkgDir) {
    $remaining = @(Get-ChildItem -LiteralPath $pkgDir -Filter '*.yaml' -File -ErrorAction SilentlyContinue)
    if ($remaining.Count -eq 0) {
        Write-Host ""
        Write-Host "==> /config/packages/ is now empty."
        $cfg = Join-Path $HaConfig 'configuration.yaml'
        $cfgText = Get-Content -LiteralPath $cfg -Raw
        if ($cfgText -match 'packages:\s*!include_dir_named\s+packages') {
            $drop = $false
            if ($Yes) { $drop = $true }
            else {
                $ans = Read-Host "    Remove the 'packages: !include_dir_named packages' line from configuration.yaml? [y/N]"
                if ($ans -match '^(y|yes)$') { $drop = $true }
            }
            if ($drop) {
                $newCfg = $cfgText -replace '(?m)^[ \t]*packages:\s*!include_dir_named\s+packages\s*\r?\n', ''
                Set-Content -LiteralPath $cfg -Value $newCfg -NoNewline
                Write-Host "    removed 'packages:' include from configuration.yaml"
            }
        }
        # Drop the empty dir
        try { Remove-Item -LiteralPath $pkgDir -Force; Write-Host "    removed empty dir: $pkgDir" } catch {}
    } else {
        Write-Host ""
        Write-Host "==> /config/packages/ still contains $($remaining.Count) other YAML file(s)."
        Write-Host "    Leaving the 'packages:' include in configuration.yaml in place."
    }
}

Write-Host ""
Write-Host "==> HeatPump Hero uninstalled."
Write-Host ""
Write-Host "Next steps in Home Assistant:"
Write-Host "  1. Settings -> Developer Tools -> YAML -> Check Configuration  (must be green)"
Write-Host "  2. Settings -> System -> Restart Home Assistant"
Write-Host "  3. (Optional) Settings -> Dashboards -> remove the 'HeatPump Hero' entry"
Write-Host ""
Write-Host "The recorder still holds sensor.hph_* history — restoring within the"
Write-Host "recorder retention window means continuous graphs."
