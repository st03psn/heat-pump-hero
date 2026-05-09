# Database recommendations

🌐 English

HA's recorder uses **SQLite** by default. HeishaHub doesn't change that —
but for heat-pump installs the recorder load is non-trivial (1-second
MQTT updates × 47 Heishamon entities = ~4 M rows / week). Below is when
SQLite is fine and when to switch.

## Decision matrix

| Profile | Recommendation |
|---|---|
| 1 heat pump, ≤ 1 year retention, single user | **SQLite** (default) — fine. |
| Heat pump + PV + many smart-home devices, 1–3 years retention | **MariaDB** — switch and you'll feel it. |
| Multi-year analytical queries, JAZ/MAZ across years | **InfluxDB** mirror in addition — keep HA recorder for state, InfluxDB for analytics. |
| Multi-site, central monitoring | **PostgreSQL** + InfluxDB. |

## Rule of thumb

If `Settings → System → Storage → Database size` is more than 1 GB and
the HA UI feels sluggish on history queries → switch to MariaDB. The
official recorder docs cover the migration:
https://www.home-assistant.io/integrations/recorder/#custom-database-engines

## SQLite tuning (cheap wins before switching)

In `configuration.yaml`:

```yaml
recorder:
  purge_keep_days: 30        # default is 10 — keep 30 for HeishaHub comparisons
  commit_interval: 5
  exclude:
    entity_globs:
      - sensor.heishahub_source_*    # facade sensors duplicate the underlying
      - sensor.heishahub_pressure_7d_mean
      - sensor.heishahub_pressure_delta_7d
    entities:
      - sensor.uptime
      - sensor.last_boot
```

Excluding the source-facade sensors saves ~30 % of HeishaHub's row volume
because the underlying heat-pump entity is recorded anyway.

## MariaDB / PostgreSQL setup

Both are HA-supported out of the box. Add the connection string to
`configuration.yaml`:

```yaml
recorder:
  db_url: mysql://user:pass@core-mariadb/homeassistant?charset=utf8mb4
  # or:
  # db_url: postgresql://user:pass@core-postgres/homeassistant
```

Use the official MariaDB / PostgreSQL HA add-ons for least-pain setup.

## InfluxDB for long-term analytics

HeishaHub's Grafana boards (`grafana/efficiency_jaz_maz.json`) expect
InfluxDB v2. Pair with the HA InfluxDB integration; HA writes
duplicate state to Influx, you query for multi-year SCOP / MAZ from
Grafana. Keep HA recorder retention shorter (e.g. 30 days), let
InfluxDB handle the long view.

This is the pattern we recommend for v0.4+ installs: **SQLite or
MariaDB for HA recorder + InfluxDB for analytics**.

## What HeishaHub itself stores

Nothing extra outside HA's recorder. Everything is HA template sensors,
utility_meter counters, statistics platform sensors, input_text /
input_number / input_select helpers. Migration between recorder DB
engines preserves all HeishaHub data automatically.
