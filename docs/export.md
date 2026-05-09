# Export

🌐 English

Three ways to get HeatPump Hero data out for external analysis.

## 1. Built-in HA UI (manual)

Settings → Developer Tools → Statistics → pick entity → ⋯ → Download.
Good for one-off Excel checks. No setup.

## 2. Scheduled CSV / JSON / XLSX (HeatPump Hero export module)

Helpers added by `packages/hph_export.yaml`:

| Helper | Purpose |
|---|---|
| `input_text.hph_export_target_path` | output directory (default `/config/hph_exports`) |
| `input_select.hph_export_format` | csv / json / xlsx |
| `input_select.hph_export_period` | last_day / last_week / last_month / last_year / all_time |
| `input_select.hph_export_schedule` | manual_only / daily_0300 / weekly_monday_0300 / monthly_1st_0300 |
| `script.hph_export_now` | manual trigger button |

**One-time setup** in `configuration.yaml`:

```yaml
shell_command:
  hph_export: >-
    HA_BASE_URL=http://localhost:8123
    HA_TOKEN=!secret hph_export_token
    HEISHAHUB_TARGET={{ states('input_text.hph_export_target_path') }}
    HEISHAHUB_FORMAT={{ states('input_select.hph_export_format') }}
    HEISHAHUB_PERIOD={{ states('input_select.hph_export_period') }}
    python3 /config/scripts/export_hph.py
```

Then in `secrets.yaml`:
```yaml
hph_export_token: <your long-lived access token>
```

Long-lived token: HA → user profile (bottom-left) → Security → Long-lived
access tokens → Create.

Runs the script at `scripts/export_hph.py` (installed by
`scripts/install.sh`). One file per entity, named
`hph_<entity>_<period>_<timestamp>.<ext>`.

For XLSX: `pip install openpyxl` in the HA Python environment, or stay
on CSV/JSON.

## 3. InfluxDB → CSV

If you already use the HA → InfluxDB integration plus our Grafana
boards, Grafana's panel menu has *Inspect → Data → Download CSV* for
any chart. Best for long-range analytical queries.

## File contents

CSV columns: `entity_id, last_changed, state, unit_of_measurement`.
JSON: array of HA history records as returned by `/api/history/period`.
XLSX: same columns as CSV, one sheet per entity.

## Common destinations

The export module writes to a local directory. To ship files elsewhere:

- **Network share** — set `target_path` to e.g. `/share/hph_exports`
  (the HA `share` add-on directory) and let your NAS pull from it.
- **Cloud storage** — chain a second automation that calls
  `notify.dropbox` / `rclone` / a `shell_command` after the export.
- **Email** — automation with `notify.smtp` after export,
  attach the latest file from the target directory.

See `tests/example_export_destinations.yaml` for working snippets _(planned in v0.5.1)_.
