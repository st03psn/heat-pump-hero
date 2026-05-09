# Import

🌐 English

Backfill HA's long-term statistics with data from before Heat Pump Hero was
installed — old Shelly / vendor cloud / utility-meter exports / a
previous HA install.

## Mechanism

HA exposes the websocket call `recorder/import_statistics` (since 2022.7).
Heat Pump Hero provides `scripts/import_csv_to_ha_stats.py` as a thin wrapper:
read CSV → call websocket → done.

## CSV format

Header row required. Hourly cadence is the most reliable; HA aggregates
to daily/monthly internally.

```csv
timestamp,state,sum
2024-01-01T00:00:00+00:00,12345.67,12345.67
2024-01-01T01:00:00+00:00,12346.89,12346.89
2024-02-01T00:00:00+00:00,13456.78,13456.78
```

| Column | Type | Notes |
|---|---|---|
| `timestamp` | ISO 8601 with timezone | hour boundary preferred |
| `state` | float | meter reading at that timestamp (cumulative) |
| `sum` | float | cumulative since recorder start (typically same as `state`) |

For a `total_increasing` energy sensor, `state == sum`. For non-cumulative
measurements (live COP, temperatures), this script is the wrong tool —
use HA's `recorder.statistics` directly.

## Usage

1. Create the target sensor in Heat Pump Hero (e.g. switch the electrical
   source to `external_energy` and point at a new `sensor.legacy_kwh_meter`).
2. Make sure the entity exists in HA at least once.
3. Prepare the CSV.
4. Install dependency: `pip install websocket-client`.
5. Run:

```bash
HA_BASE_URL=http://homeassistant.local:8123 \
HA_TOKEN=<long-lived-token> \
python3 scripts/import_csv_to_ha_stats.py \
    --entity sensor.legacy_kwh_meter \
    --unit kWh \
    --csv old_meter_data.csv
```

6. Verify in Settings → Developer Tools → Statistics → pick the entity
   → graph should show the imported history.

## Common sources

| Source | Export method to CSV |
|---|---|
| Shelly cloud | Shelly app → Statistics → Export CSV |
| Aquarea Smart Cloud | service-cloud.panasonic.com → Reports → Download |
| Utility-company portal (Stromnetz/E.ON/EnBW/...) | usually a yearly CSV under "consumption history" |
| Previous HA install | Use `scripts/export_hph.py` on the old install, copy CSV across |
| Tibber | Tibber API → daily consumption → format columns |

## Caveats

- HA's import treats the data as authoritative; importing again with
  overlapping timestamps overwrites.
- Backup HA's recorder DB before bulk imports.
- Importing into a `total_increasing` entity that already has live data:
  ensure timestamps don't overlap, otherwise sum jumps appear.
- The websocket call requires `homeassistant >= 2022.7`. Heat Pump Hero min
  is 2024.4 so this is satisfied by default.
