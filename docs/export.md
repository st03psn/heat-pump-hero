# Export

🌐 English

Three ways to get HeatPump Hero data out for external analysis.

## 1. Built-in HA UI (manual)

Settings → Developer Tools → Statistics → pick entity → ⋯ → Download.
Good for one-off Excel checks. No setup.

## 2. Scheduled CSV / JSON / XLSX (HeatPump Hero export service)

Since v0.9 the export is a Python service registered by the integration
— no `shell_command:` setup, no long-lived token to wire up.

**Configuration entities** (set via the dashboard's *Configuration → Export*
section, or directly):

| Entity | Purpose |
|---|---|
| `text.hph_export_target_path` | output directory (default `/config/hph/exports`) |
| `select.hph_export_format` | csv / json / xlsx |
| `select.hph_export_period` | last_day / last_week / last_month / last_year / all_time |
| `select.hph_export_schedule` | manual_only / daily_0300 / weekly_monday_0300 / monthly_1st_0300 |
| `button.hph_export_now` | manual trigger |

**Service:** `hph.export_now` — runnable from *Developer Tools → Services*
or from any HA automation. Honours the configured format / period /
target. Posts a persistent notification on completion.

**Scheduled runs:** select a non-manual schedule in
`select.hph_export_schedule`; the integration's coordinator fires the
export at the configured time without any external scheduler.

For XLSX: `pip install openpyxl` in the HA Python environment, or stay
on CSV/JSON. The service falls back to CSV automatically if `openpyxl`
isn't available.

## 3. InfluxDB → CSV

If you already use the HA → InfluxDB integration plus our Grafana
boards, Grafana's panel menu has *Inspect → Data → Download CSV* for
any chart. Best for long-range analytical queries.

## File contents

CSV columns: `entity_id, last_changed, state, unit_of_measurement`.
JSON: array of HA history records as returned by `/api/history/period`.
XLSX: same columns as CSV, one sheet per entity.

Files are named `hph_<entity>_<period>_<timestamp>.<ext>`. If the
configured `target_path` already exists as a directory or has no
extension, the integration writes
`hph_export_<timestamp>.<fmt>` inside it (preventing the
"export creates a directory instead of a file" bug from v0.8).

## Common destinations

The export service writes to a local directory. To ship files elsewhere:

- **Network share** — set `target_path` to e.g. `/share/hph_exports`
  (the HA `share` add-on directory) and let your NAS pull from it.
- **Cloud storage** — chain a second automation triggered after the
  export's persistent notification, calling `notify.dropbox` / `rclone` /
  a `shell_command`.
- **Email** — automation with `notify.smtp` after export, attaching the
  latest file from the target directory.

## Legacy: shell-command export (pre-v0.9)

Earlier versions wired up `shell_command.hph_export` calling
`scripts/export_heishahub.py`. This still works if you've kept the
script and `configuration.yaml` snippet around, but the integration's
`hph.export_now` service supersedes it. Plan to remove the legacy path
in v1.0.
