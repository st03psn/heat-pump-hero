#!/usr/bin/env bash
#
# HeatPump Hero — CLI installer
# Copies packages, dashboard, blueprint, scripts into an existing HA config.
# Idempotent. Performs prereq checks and offers DB recommendations.
#
# Usage:
#   ./scripts/install.sh /path/to/homeassistant/config [--db sqlite|mariadb|postgresql]
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HA_CONFIG=""
DB_CHOICE=""

# ─── argv parsing ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --db)
            DB_CHOICE="$2"
            shift 2
            ;;
        --db=*)
            DB_CHOICE="${1#*=}"
            shift
            ;;
        -h|--help)
            cat <<EOF
Usage: $0 <ha-config-dir> [--db sqlite|mariadb|postgresql]

  <ha-config-dir>     HA config directory (e.g. /config or ~/homeassistant)
  --db                Database backend recommendation (default: ask)

Examples:
  $0 /config
  $0 /config --db mariadb
EOF
            exit 0
            ;;
        *)
            if [[ -z "$HA_CONFIG" ]]; then
                HA_CONFIG="$1"
            fi
            shift
            ;;
    esac
done

if [[ -z "$HA_CONFIG" ]]; then
    echo "ERROR: HA config directory required."
    echo "Usage: $0 <ha-config-dir> [--db sqlite|mariadb|postgresql]"
    exit 1
fi

if [[ ! -f "$HA_CONFIG/configuration.yaml" ]]; then
    echo "ERROR: $HA_CONFIG/configuration.yaml not found."
    exit 1
fi

# ─── prereq check ─────────────────────────────────────────────────────────
echo "==> HeatPump Hero installer"
echo "==> Pre-flight checks"

missing=()
warn() { echo "    [warn] $1"; }
ok()   { echo "    [ ok ] $1"; }

# Python 3 (used by export/import/analyze scripts and by this installer)
if ! command -v python3 >/dev/null 2>&1; then
    missing+=("python3")
    warn "python3 not on PATH — required for export/analyze scripts"
else
    ok "python3 present ($(python3 --version 2>&1))"
fi

# MQTT addon presence
if [[ -d "$HA_CONFIG/.." ]] && find "$HA_CONFIG/.." -maxdepth 3 -type d -name 'addons*' 2>/dev/null | head -1 | grep -q . ; then
    ok "HA add-ons directory visible"
else
    warn "HA add-ons directory not visible — MQTT broker setup must be checked manually"
fi

# Heishamon kamaradclimber integration check
if find "$HA_CONFIG/custom_components" -maxdepth 2 -type d -name 'heishamon*' 2>/dev/null | head -1 | grep -q . ; then
    ok "kamaradclimber/heishamon-homeassistant detected in custom_components/"
else
    warn "kamaradclimber heishamon integration not found — install it via HACS first"
fi

# HACS frontend dependencies
declare -A HACS_DEPS=(
    [apexcharts-card]="ApexCharts (chart rendering)"
    [bubble-card]="Bubble-Card (schematic)"
    [mushroom]="Lovelace Mushroom (status tiles)"
    [button-card]="Button-Card (conditional logic)"
    [auto-entities]="auto-entities (heat-curve filter)"
    [card-mod]="card-mod (style overrides)"
)
for dep in "${!HACS_DEPS[@]}"; do
    if find "$HA_CONFIG/www/community" -maxdepth 2 -type d -iname "*${dep}*" 2>/dev/null | head -1 | grep -q . ; then
        ok "$dep present"
    else
        warn "$dep missing — ${HACS_DEPS[$dep]} (install via HACS)"
    fi
done

if (( ${#missing[@]} )); then
    echo
    echo "ERROR: required prerequisites missing: ${missing[*]}"
    echo "Install them and re-run."
    exit 2
fi

# ─── DB recommendation ────────────────────────────────────────────────────
if [[ -z "$DB_CHOICE" ]]; then
    cat <<EOF

==> Database recommendation
    HeatPump Hero stores everything via HA's recorder. Picking the
    right backend matters for long-term performance:

    [1] sqlite      — default, fine for ≤1 year retention, single user
    [2] mariadb     — recommended for ≥1 year retention, multi-device installs
    [3] postgresql  — multi-site / heavy analytical queries
    [4] keep current configuration (don't change recorder)

EOF
    read -r -p "    Choose [1-4] (default 4): " choice
    case "${choice:-4}" in
        1) DB_CHOICE=sqlite ;;
        2) DB_CHOICE=mariadb ;;
        3) DB_CHOICE=postgresql ;;
        *) DB_CHOICE=skip ;;
    esac
fi

case "$DB_CHOICE" in
    sqlite)
        echo "==> Database: SQLite (default — no configuration change needed)"
        ;;
    mariadb)
        cat <<'EOF'
==> Database: MariaDB selected.
    Action required from you:
      1. Install the official "MariaDB" HA add-on (Settings → Add-ons).
      2. Add to configuration.yaml:
           recorder:
             db_url: mysql://homeassistant:<password>@core-mariadb/homeassistant?charset=utf8mb4
      3. Restart HA. Existing SQLite data is NOT migrated automatically —
         see docs/database.md for the migration script.
EOF
        ;;
    postgresql)
        cat <<'EOF'
==> Database: PostgreSQL selected.
    Action required from you:
      1. Install PostgreSQL (HA add-on or external).
      2. Add to configuration.yaml:
           recorder:
             db_url: postgresql://homeassistant:<password>@<host>/homeassistant
      3. Restart HA. See docs/database.md for migration notes.
EOF
        ;;
    skip|*)
        echo "==> Database: keeping current recorder config."
        ;;
esac

# ─── file copy ────────────────────────────────────────────────────────────
echo "==> Installing files"

# 1. Packages
mkdir -p "$HA_CONFIG/packages"
for f in "$SCRIPT_DIR"/packages/*.yaml; do
    name="$(basename "$f")"
    echo "    packages/$name"
    cp "$f" "$HA_CONFIG/packages/$name"
done

# 2. Dashboard
mkdir -p "$HA_CONFIG/hph"
cp "$SCRIPT_DIR/dashboards/hph.yaml" "$HA_CONFIG/hph/dashboard.yaml"
mkdir -p "$HA_CONFIG/www/hph"
cp -r "$SCRIPT_DIR/dashboards/assets/." "$HA_CONFIG/www/hph/"
echo "    www/hph/  (SVG assets)"

# 3. Blueprint
mkdir -p "$HA_CONFIG/blueprints/script/hph"
cp "$SCRIPT_DIR/blueprints/hph_setup.yaml" \
   "$HA_CONFIG/blueprints/script/hph/hph_setup.yaml"

# 4. Scripts (export, import, heating-curve analyzer)
mkdir -p "$HA_CONFIG/scripts"
for f in export_heishahub.py import_csv_to_ha_stats.py analyze_heating_curve.py; do
    if [[ -f "$SCRIPT_DIR/scripts/$f" ]]; then
        cp "$SCRIPT_DIR/scripts/$f" "$HA_CONFIG/scripts/$f"
        chmod +x "$HA_CONFIG/scripts/$f"
        echo "    scripts/$f"
    fi
done

# 5. configuration.yaml — add packages include if missing
if ! grep -q "packages: !include_dir_named packages" "$HA_CONFIG/configuration.yaml"; then
    echo "==> Adding 'packages: !include_dir_named packages' to configuration.yaml"
    if grep -q "^homeassistant:" "$HA_CONFIG/configuration.yaml"; then
        python3 - "$HA_CONFIG/configuration.yaml" <<'PY'
import sys, re
path = sys.argv[1]
src = open(path).read()
src = re.sub(
    r'(^homeassistant:\s*\n)',
    r'\1  packages: !include_dir_named packages\n',
    src, count=1, flags=re.M
)
open(path, 'w').write(src)
PY
    else
        printf '\nhomeassistant:\n  packages: !include_dir_named packages\n' \
            >> "$HA_CONFIG/configuration.yaml"
    fi
fi

cat <<EOF

==> HeatPump Hero installed.

Next steps in Home Assistant:
  1. Restart HA (Settings → System → Restart).
  2. Run "HeatPump Hero Setup" blueprint
     (Settings → Automations → Blueprints).
  3. Add dashboard:
     Settings → Dashboards → Add Dashboard → From YAML
     → file: hph/dashboard.yaml
  4. Configure sources (vendor preset / model / external sensors)
     in the dashboard "Configuration" view.
  5. (Optional) Indoor-temp analysis: set
     input_text.hph_indoor_temp_entity to your reference room sensor.
  6. (Optional) Schedule export / heating-curve analysis — see
     docs/export.md and docs/import.md.

Done.
EOF
