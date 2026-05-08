#!/usr/bin/env bash
#
# HeishaHub — CLI-Installer
# Kopiert Packages, Dashboard und Blueprint in eine bestehende
# Home-Assistant-Konfiguration. Idempotent.
#
# Usage:
#   ./scripts/install.sh /path/to/homeassistant/config
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HA_CONFIG="${1:-}"

if [[ -z "$HA_CONFIG" ]]; then
    echo "Usage: $0 <ha-config-dir>"
    echo "Example: $0 /config   (HassOS)"
    echo "         $0 ~/homeassistant"
    exit 1
fi

if [[ ! -f "$HA_CONFIG/configuration.yaml" ]]; then
    echo "ERROR: $HA_CONFIG/configuration.yaml not found."
    exit 1
fi

echo "==> Installing HeishaHub into $HA_CONFIG"

# 1. Packages
mkdir -p "$HA_CONFIG/packages"
for f in "$SCRIPT_DIR"/packages/*.yaml; do
    name="$(basename "$f")"
    echo "    packages/$name"
    cp "$f" "$HA_CONFIG/packages/$name"
done

# 2. Dashboard
mkdir -p "$HA_CONFIG/heishahub"
cp "$SCRIPT_DIR/dashboards/heishahub.yaml" "$HA_CONFIG/heishahub/dashboard.yaml"
mkdir -p "$HA_CONFIG/www/heishahub"
cp -r "$SCRIPT_DIR/dashboards/assets/." "$HA_CONFIG/www/heishahub/"
echo "    www/heishahub/  (SVG-Assets)"

# 3. Blueprint
mkdir -p "$HA_CONFIG/blueprints/script/heishahub"
cp "$SCRIPT_DIR/blueprints/heishahub_setup.yaml" \
   "$HA_CONFIG/blueprints/script/heishahub/heishahub_setup.yaml"

# 4. configuration.yaml ergänzen (idempotent)
if ! grep -q "packages: !include_dir_named packages" "$HA_CONFIG/configuration.yaml"; then
    echo "==> Adding 'packages: !include_dir_named packages' to configuration.yaml"
    if grep -q "^homeassistant:" "$HA_CONFIG/configuration.yaml"; then
        # Append unter homeassistant:
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

==> HeishaHub installed.

Next steps in Home Assistant:
  1. Restart Home Assistant (Settings → System → Restart).
  2. Run the "HeishaHub Setup" script blueprint
     (Settings → Automations → Blueprints).
  3. Add dashboard:
     Settings → Dashboards → Add Dashboard → From YAML
     → file: heishahub/dashboard.yaml
  4. (Optional) Configure external sensors:
     Settings → Devices & Services → Helpers → heishahub_*

Done.
EOF
