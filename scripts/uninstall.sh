#!/usr/bin/env bash
#
# HeatPump Hero — CLI uninstaller
#
# Removes every file the installer ever wrote into a HA config directory.
# Does NOT touch:
#   - HA's recorder DB (state history of sensor.hph_* stays intact until
#     the configured retention window expires, then naturally drops)
#   - Long-Term Statistics
#   - configuration.yaml itself (only the `packages: !include_dir_named
#     packages` line — and only if /config/packages/ is now empty)
#   - HACS-installed integrations or frontend cards
#
# Idempotent. Run repeatedly without harm.
#
# Usage:
#   ./scripts/uninstall.sh /path/to/homeassistant/config [--dry-run] [--yes]
#
set -euo pipefail

HA_CONFIG=""
DRY_RUN=0
ASSUME_YES=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run|-n)
            DRY_RUN=1
            shift
            ;;
        --yes|-y)
            ASSUME_YES=1
            shift
            ;;
        -h|--help)
            cat <<EOF
Usage: $0 <ha-config-dir> [--dry-run] [--yes]

  <ha-config-dir>     HA config directory (e.g. /config or ~/homeassistant)
  --dry-run, -n       List what would be removed, do nothing
  --yes, -y           Don't prompt before deleting

Examples:
  $0 /config --dry-run
  $0 /config --yes
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
    echo "Usage: $0 <ha-config-dir> [--dry-run] [--yes]"
    exit 1
fi

if [[ ! -f "$HA_CONFIG/configuration.yaml" ]]; then
    echo "ERROR: $HA_CONFIG/configuration.yaml not found — wrong directory?"
    exit 1
fi

echo "==> HeatPump Hero uninstaller"
echo "    Target: $HA_CONFIG"
[[ $DRY_RUN -eq 1 ]] && echo "    Mode:   DRY RUN (no changes)"

# Collect targets first so we can show a single confirmation prompt.
declare -a TARGETS=()

# 1. Packages — every hph_*.yaml in /config/packages/
if [[ -d "$HA_CONFIG/packages" ]]; then
    while IFS= read -r f; do
        TARGETS+=("$f")
    done < <(find "$HA_CONFIG/packages" -maxdepth 1 -type f -name 'hph_*.yaml' 2>/dev/null)
fi

# 2. Dashboard YAML
[[ -f "$HA_CONFIG/hph/dashboard.yaml" ]] && TARGETS+=("$HA_CONFIG/hph/dashboard.yaml")
[[ -d "$HA_CONFIG/hph" ]] && TARGETS+=("$HA_CONFIG/hph")

# 3. Dashboard SVG / asset directory
[[ -d "$HA_CONFIG/www/hph" ]] && TARGETS+=("$HA_CONFIG/www/hph")

# 4. Setup blueprint
[[ -f "$HA_CONFIG/blueprints/script/hph/hph_setup.yaml" ]] && \
    TARGETS+=("$HA_CONFIG/blueprints/script/hph/hph_setup.yaml")
[[ -d "$HA_CONFIG/blueprints/script/hph" ]] && \
    TARGETS+=("$HA_CONFIG/blueprints/script/hph")

# 5. Helper Python scripts
for f in export_heishahub.py import_csv_to_ha_stats.py analyze_heating_curve.py; do
    [[ -f "$HA_CONFIG/scripts/$f" ]] && TARGETS+=("$HA_CONFIG/scripts/$f")
done

# 6. Optional CSV export directory under www/heishahub_exports — only
#    listed for visibility; NOT removed by default (user data).
EXPORT_DIR="$HA_CONFIG/www/heishahub_exports"

if (( ${#TARGETS[@]} == 0 )); then
    echo "==> Nothing to remove. HeatPump Hero is not installed in this config dir."
    exit 0
fi

echo
echo "==> Files / directories that will be removed:"
for t in "${TARGETS[@]}"; do
    echo "    $t"
done

if [[ -d "$EXPORT_DIR" ]]; then
    echo
    echo "==> Note: user data NOT touched:"
    echo "    $EXPORT_DIR  (your CSV / JSON / XLSX exports — delete manually if wanted)"
fi

echo
echo "==> NOT touched (by design):"
echo "    Recorder DB / Long-Term Statistics — sensor.hph_* history stays"
echo "    intact and naturally drops once the recorder retention window expires."
echo "    HACS integrations and frontend cards — manage via HACS."

if [[ $DRY_RUN -eq 1 ]]; then
    echo
    echo "==> DRY RUN — exiting without changes."
    exit 0
fi

if [[ $ASSUME_YES -eq 0 ]]; then
    echo
    read -r -p "Proceed? [y/N] " confirm
    case "${confirm:-N}" in
        y|Y|yes|YES) ;;
        *) echo "Aborted."; exit 1 ;;
    esac
fi

# ─── perform removals ─────────────────────────────────────────────────────
echo "==> Removing"
# Files first, then dirs (find returns deepest-last is not guaranteed; sort
# by length descending so children come before parents).
mapfile -t SORTED < <(printf '%s\n' "${TARGETS[@]}" | awk '{print length, $0}' | sort -rn | cut -d' ' -f2-)
for t in "${SORTED[@]}"; do
    if [[ -f "$t" ]]; then
        rm -f -- "$t"
        echo "    removed file: $t"
    elif [[ -d "$t" ]]; then
        # Only remove if empty (children were already deleted by the file pass)
        if [[ -z "$(ls -A "$t" 2>/dev/null)" ]]; then
            rmdir -- "$t"
            echo "    removed dir:  $t"
        else
            echo "    kept dir:     $t  (not empty — contains user files)"
        fi
    fi
done

# 7. Optional: clean `packages: !include_dir_named packages` if /config/packages/
#    is now empty. Only do this if no other YAMLs remain — otherwise the user
#    has their own packages and we leave the include alone.
if [[ -d "$HA_CONFIG/packages" ]]; then
    remaining=$(find "$HA_CONFIG/packages" -maxdepth 1 -type f -name '*.yaml' 2>/dev/null | wc -l)
    if (( remaining == 0 )); then
        echo
        echo "==> /config/packages/ is now empty."
        if grep -q "packages: !include_dir_named packages" "$HA_CONFIG/configuration.yaml"; then
            if [[ $ASSUME_YES -eq 1 ]]; then
                drop_include=1
            else
                read -r -p "    Remove the 'packages: !include_dir_named packages' line from configuration.yaml? [y/N] " ans
                case "${ans:-N}" in
                    y|Y|yes|YES) drop_include=1 ;;
                    *) drop_include=0 ;;
                esac
            fi
            if [[ ${drop_include:-0} -eq 1 ]]; then
                python3 - "$HA_CONFIG/configuration.yaml" <<'PY'
import sys, re
p = sys.argv[1]
src = open(p).read()
new = re.sub(r'^[ \t]*packages: !include_dir_named packages\s*\n', '', src, flags=re.M)
if new != src:
    open(p, 'w').write(new)
    print("    removed 'packages:' include from configuration.yaml")
PY
            fi
        fi
        # Optionally drop the empty packages dir
        rmdir "$HA_CONFIG/packages" 2>/dev/null && echo "    removed empty dir: $HA_CONFIG/packages" || true
    else
        echo
        echo "==> /config/packages/ still contains $remaining other YAML file(s)."
        echo "    Leaving the 'packages:' include in configuration.yaml in place."
    fi
fi

cat <<EOF

==> HeatPump Hero uninstalled.

Next steps in Home Assistant:
  1. Settings → Developer Tools → YAML → Check Configuration  (must be green)
  2. Settings → System → Restart Home Assistant
  3. (Optional) Settings → Dashboards → remove the "HeatPump Hero"
     dashboard entry if you added it manually.
  4. (Optional) Settings → Devices → Helpers → Restored entities —
     anything starting with "hph_" can be restored if you reinstall later.

The recorder still holds sensor.hph_* history — restoring within the
recorder retention window means continuous graphs.

Done.
EOF
