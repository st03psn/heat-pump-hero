# HeatPump Hero — developer deploy (v0.9 Python integration)
#
# Syncs the full custom_components/hph/ tree to a running HA instance
# exposed via Samba or a mounted drive. Excludes __pycache__ and .pyc files.
# Also keeps dashboards/hph.yaml in sync with both deploy targets.
#
# Usage:
#   .\scripts\deploy_dev.ps1                        # uses default P:\
#   .\scripts\deploy_dev.ps1 -HaConfig \\ha\config
#   .\scripts\deploy_dev.ps1 -HaConfig P:\ -Reload  # also triggers HPH reload via REST API

[CmdletBinding()]
param(
    [string] $HaConfig = 'P:\',
    [switch] $Reload
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path -LiteralPath (Join-Path $HaConfig 'configuration.yaml'))) {
    throw "configuration.yaml not found under $HaConfig — is the share mounted?"
}

Write-Host "==> HPH deploy  repo → $HaConfig"

# ── 1. custom_components/hph/ (full mirror, excludes __pycache__) ────────────
$srcCC  = Join-Path $repoRoot 'custom_components\hph'
$dstCC  = Join-Path $HaConfig 'custom_components\hph'

& robocopy $srcCC $dstCC /MIR /XD __pycache__ /XF *.pyc /NJH /NJS /NDL | Out-Null
# robocopy exit codes 0-7 are success variants (0=no change, 1=copied, 2=extra in dst, etc.)
if ($LASTEXITCODE -ge 8) {
    throw "robocopy failed (exit $LASTEXITCODE). Check paths and permissions."
}
Write-Host "    custom_components/hph/  synced (robocopy exit $LASTEXITCODE)"

# ── 2. Dashboard — two deploy targets ────────────────────────────────────────
# Target A: bootstrap source (copied to <config>/hph/dashboard.yaml on reload)
$srcDash   = Join-Path $repoRoot 'custom_components\hph\data\dashboards\hph.yaml'
$dstDashA  = Join-Path $HaConfig 'custom_components\hph\data\dashboards\hph.yaml'  # already mirrored above
$dstDashB  = Join-Path $HaConfig 'hph\dashboard.yaml'

if (Test-Path (Split-Path $dstDashB)) {
    Copy-Item -LiteralPath $srcDash -Destination $dstDashB -Force
    Write-Host "    hph/dashboard.yaml"
}

# ── 3. dashboards/hph.yaml (repo root — CI reference copy) ──────────────────
$rootDash    = Join-Path $repoRoot 'dashboards\hph.yaml'
$intDash     = Join-Path $repoRoot 'custom_components\hph\data\dashboards\hph.yaml'
if ((Get-FileHash $rootDash).Hash -ne (Get-FileHash $intDash).Hash) {
    Write-Warning "dashboards/hph.yaml differs from custom_components/…/dashboards/hph.yaml — run smoke test to check."
}

# ── 4. Optional: reload HPH via REST API ────────────────────────────────────
if ($Reload) {
    $tokenFile = Join-Path $env:USERPROFILE '.claude\projects\D--DEV-heat-pump-hero\memory\ha_token.md'
    if (-not (Test-Path $tokenFile)) {
        Write-Warning "-Reload: token file not found at $tokenFile — skipping reload."
    } else {
        $content = Get-Content $tokenFile -Raw
        if ($content -match 'token[`:\s]+([A-Za-z0-9._-]{20,})') {
            $token = $matches[1]
        }
        if ($content -match 'url[`:\s]+(https?://[^\s]+)') {
            $haUrl = $matches[1].TrimEnd('/')
        }
        if ($token -and $haUrl) {
            $headers = @{ Authorization = "Bearer $token"; 'Content-Type' = 'application/json' }
            # Find HPH config entry ID
            $entries = Invoke-RestMethod "$haUrl/api/config/config_entries/entry" -Headers $headers
            $hph = $entries | Where-Object { $_.domain -eq 'hph' } | Select-Object -First 1
            if ($hph) {
                Invoke-RestMethod "$haUrl/api/config/config_entries/entry/$($hph.entry_id)/reload" `
                    -Method POST -Headers $headers | Out-Null
                Write-Host "    HPH reload triggered (entry $($hph.entry_id))"
            } else {
                Write-Warning "-Reload: no 'hph' config entry found via API."
            }
        } else {
            Write-Warning "-Reload: could not parse token/url from $tokenFile."
        }
    }
}

Write-Host ""
Write-Host "==> Deploy complete."
if (-not $Reload) {
    Write-Host "    Reload HPH in HA: Developer Tools → YAML → Reload All  (or -Reload flag)"
}
exit 0
