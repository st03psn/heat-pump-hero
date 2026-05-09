# Installation

🌐 English (this file) · [Deutsch](de/installation.md)

## Prerequisites

| Component | Minimum version | Source |
|---|---|---|
| Home Assistant | 2025.4 | hass |
| HACS | 2.0 | https://hacs.xyz |
| MQTT broker | any | e.g. Mosquitto add-on |
| Heishamon hardware | recent Egyras / IgorYbema firmware | https://github.com/Egyras/HeishaMon |

Optional, for long-term statistics:
- InfluxDB add-on
- Grafana add-on

## Step 1 — Install the Heishamon integration

In HACS:

1. *Integrations* → ⋮ → *Custom repositories*
2. URL: `https://github.com/kamaradclimber/heishamon-homeassistant`
3. Category: *Integration*
4. Install *Heishamon*, then restart Home Assistant.
5. Settings → Devices & Services — MQTT auto-discovery should pick up the
   heat pump. Verify the topic prefix (default: `panasonic_heat_pump`).

## Step 2 — Install frontend plugins

In HACS *Frontend*, search and install:

- ApexCharts Card
- Bubble Card
- Mushroom
- button-card
- auto-entities
- card-mod

## Step 3 — Get the Heat Pump Hero repo

```bash
cd /tmp
git clone https://github.com/st03psn/heat-pump-hero.git
```

## Step 4 — Run the installer (recommended)

```bash
cd Heat Pump Hero
./scripts/install.sh /path/to/your/homeassistant/config
```

The installer copies:
- `packages/*.yaml` → `<config>/packages/`
- `dashboards/hph.yaml` → `<config>/hph/dashboard.yaml`
- `dashboards/assets/*.svg` → `<config>/www/hph/`
- `blueprints/hph_setup.yaml` → `<config>/blueprints/script/hph/`

and idempotently adds `homeassistant: packages: !include_dir_named packages`
to `configuration.yaml`.

### Manual install (alternative)

If you don't have shell access, copy the four directories manually (e.g.
through the *File Editor* add-on) and append the line above to
`configuration.yaml`.

## Step 5 — Restart Home Assistant

`Settings → System → Restart`. After the restart, filter for `hph_` in
*Developer Tools → States* — the Heat Pump Hero sensors should appear.

## Step 6 — Run the setup blueprint

`Settings → Automations & Scenes → Blueprints` → *Heat Pump Hero Setup* →
*Create script* → run it. It posts a persistent notification reporting
whether your Heishamon entities were detected.

## Step 7 — Add the dashboard

`Settings → Dashboards → Add Dashboard → From YAML`:

```yaml
title: Heat Pump Hero
icon: mdi:heat-pump
mode: yaml
filename: hph/dashboard.yaml
```

## Step 8 — (Optional) external sensors

See [external_sensors.md](external_sensors.md).

## Step 9 — (Optional) Grafana / InfluxDB

1. Install the **InfluxDB add-on**, create a bucket `hph`, generate a token.
2. Configure the **HA InfluxDB integration** — it mirrors all
   `sensor.hph_*` to InfluxDB.
3. Alternatively, run **Telegraf** with `grafana/telegraf_mqtt.conf` for a
   direct MQTT → InfluxDB path (higher resolution, no HA recorder limits).
4. Start the **Grafana add-on**, add the InfluxDB datasource, import
   `grafana/overview.json` and `grafana/efficiency_jaz_maz.json`.

## Coexistence with HeishaMoNR (Node-Red)

Both systems can listen on the same MQTT broker. **Only one** should write.
While testing in parallel:

- HeishaMoNR controls (schedules, CCC, RTC, SoftStart),
- Heat Pump Hero reads and visualizes only — disable all `number.*` and
  `select.*` entities of the kamaradclimber integration in HA
  (Entity → Disable).

## Updating

```bash
cd /tmp/Heat Pump Hero
git pull
./scripts/install.sh /path/to/your/homeassistant/config
```

Existing helper values (source selection, external entity-IDs) are preserved
because the installer does not reset `input_*` entities.
