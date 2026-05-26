# Migration — Mode-aware tariff split (standby tariff)

Starting with v0.9-rc10 the `utility_meter` split entities gain a fourth
tariff `standby` alongside the existing `heating`, `dhw`, `cooling`. The
operating-mode sensor now emits `standby` whenever the compressor is not
running, so auxiliary draw (control electronics, frost protection, an
externally-permanent circulator) is routed into a dedicated tariff
instead of polluting whichever mode was last active.

Affected utility_meter parents (each fans out into `<parent>_<tariff>`):

- `sensor.hph_thermal_daily_split`
- `sensor.hph_electrical_daily_split`
- `sensor.hph_thermal_monthly_split`
- `sensor.hph_electrical_monthly_split`
- `sensor.hph_thermal_yearly_split`
- `sensor.hph_electrical_yearly_split`

## Why a migration helper

HA *should* preserve existing tariff values when a new tariff is added to
a utility_meter. Some HA versions/edge cases reset to 0 when the tariff
list changes. The helper script protects against that case by snapshotting
the current totals before the integration update and restoring them via
`utility_meter.calibrate` if anything drifted.

The script uses HA REST + service calls only — **no direct DB writes**.

## Steps (Produktivinstanz)

```bash
# 0. Set credentials (or pass via --host/--token)
export HA_BASE_URL="http://192.168.111.73:8123"
export HA_TOKEN="<long-lived-token>"

# 1. Snapshot BEFORE updating the integration
python3 scripts/migrate_mode_tariffs.py --snapshot
# → scripts/migration_backup_192.168.111.73_8123_YYYYMMDDT....json

# 2. Update HeatPump Hero (HACS update or copy custom_components/hph)
# 3. Reload the integration in HA (Settings → Devices & Services → HPH → Reload)

# 4. Verify post-state
python3 scripts/migrate_mode_tariffs.py \
    --verify scripts/migration_backup_<host>_<ts>.json
# Exit code 0 → no drift; 2 → drift detected (proceed to step 5)

# 5. Restore (if drift detected)
python3 scripts/migrate_mode_tariffs.py \
    --apply scripts/migration_backup_<host>_<ts>.json
# Re-run --verify to confirm everything is back to the snapshot values.
```

`--dry-run` works with `--apply` and prints the planned `calibrate` calls
without executing them.

## What the standby tariff captures

After the migration, `sensor.hph_electrical_yearly_split_standby` accumulates
electrical kWh consumed while the compressor is off — typical sources:

- HP control electronics (~5–15 W continuous)
- Frost protection circuits
- Externally-permanent heating-circuit circulator (50–80 W × 24 h)
- Brief residual draw during pump runout after compressor stop

The `sensor.hph_advisor_standby` advisor compares the daily standby figure
against `number.hph_advisor_standby_max_kwh` (default 0.4 kWh/day) and
raises warn/critical when the threshold is exceeded.

## Sister sensor — daily Standby

`sensor.hph_standby_electrical_daily` continues to exist alongside the new
tariff-fed total. It is a daily differential (`total − runtime_kwh`) and is
the figure shown on the Overview tile. The yearly_split_standby is the
cumulative season-long figure on the Efficiency view. Both are correct —
they answer different questions.
