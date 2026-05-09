#!/usr/bin/env bash
#
# HeatPump Hero — quick non-interactive update
#
# Use this for fast iteration during testing: copies packages, dashboard,
# blueprint and helper scripts into a HA config dir without prereq checks
# or DB prompts. Idempotent. Recorder data is untouched, so reinstall /
# uninstall / reinstall keeps your sensor.hph_* history intact.
#
# Usage:
#   ./scripts/update.sh /path/to/homeassistant/config
#
# For a first-time install with prereq checks and DB recommendation, use
# install.sh instead.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HA_CONFIG="${1:-}"

if [[ -z "$HA_CONFIG" ]]; then
    echo "Usage: $0 <ha-config-dir>"
    exit 1
fi

if [[ ! -f "$HA_CONFIG/configuration.yaml" ]]; then
    echo "ERROR: $HA_CONFIG/configuration.yaml not found — wrong directory?"
    exit 1
fi

echo "==> HeatPump Hero update — target: $HA_CONFIG"

# 1. Packages
mkdir -p "$HA_CONFIG/packages"
for f in "$SCRIPT_DIR"/packages/*.yaml; do
    name="$(basename "$f")"
    cp "$f" "$HA_CONFIG/packages/$name"
    echo "    packages/$name"
done

# 2. Dashboard
mkdir -p "$HA_CONFIG/hph"
cp "$SCRIPT_DIR/dashboards/hph.yaml" "$HA_CONFIG/hph/dashboard.yaml"
echo "    hph/dashboard.yaml"

mkdir -p "$HA_CONFIG/www/hph"
cp -r "$SCRIPT_DIR/dashboards/assets/." "$HA_CONFIG/www/hph/"
echo "    www/hph/  (SVG assets)"

# 3. Blueprint
mkdir -p "$HA_CONFIG/blueprints/script/hph"
cp "$SCRIPT_DIR/blueprints/hph_setup.yaml" \
   "$HA_CONFIG/blueprints/script/hph/hph_setup.yaml"
echo "    blueprints/script/hph/hph_setup.yaml"

# 4. Helper scripts
mkdir -p "$HA_CONFIG/scripts"
for f in export_heishahub.py import_csv_to_ha_stats.py analyze_heating_curve.py; do
    if [[ -f "$SCRIPT_DIR/scripts/$f" ]]; then
        cp "$SCRIPT_DIR/scripts/$f" "$HA_CONFIG/scripts/$f"
        chmod +x "$HA_CONFIG/scripts/$f"
        echo "    scripts/$f"
    fi
done

# 5. configuration.yaml include — only if missing
if ! grep -q "packages: !include_dir_named packages" "$HA_CONFIG/configuration.yaml"; then
    if grep -q "^homeassistant:" "$HA_CONFIG/configuration.yaml"; then
        python3 - "$HA_CONFIG/configuration.yaml" <<'PY'
import sys, re
p = sys.argv[1]
src = open(p).read()
src = re.sub(r'(^homeassistant:\s*\n)',
             r'\1  packages: !include_dir_named packages\n',
             src, count=1, flags=re.M)
open(p, 'w').write(src)
PY
    else
        printf '\nhomeassistant:\n  packages: !include_dir_named packages\n' \
            >> "$HA_CONFIG/configuration.yaml"
    fi
    echo "    (added 'packages:' include to configuration.yaml)"
fi

cat <<EOF

==> Update complete. In HA:
  Developer Tools → YAML → Check Configuration  (must be green)
  Developer Tools → YAML → All YAML configuration  (reload)
    or
  Settings → System → Restart Home Assistant   (if helpers / counters changed)
EOF
