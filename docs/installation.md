# Installation

HeatPump Hero v0.9+ ships as a **Home Assistant custom integration**
installed via HACS. There is no shell access required, no YAML to edit
in `configuration.yaml`, and no `packages/` directory to populate.

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

## Step 3 — Add the HeatPump Hero custom repository

In HACS:

1. *Integrations* → ⋮ → *Custom repositories*
2. URL: `https://github.com/st03psn/heat-pump-hero`
3. Category: *Integration*
4. Install *HeatPump Hero*, then **restart Home Assistant**.

## Step 4 — Run the configuration wizard

`Settings → Devices & Services → Add Integration → HeatPump Hero`.

The 4-step wizard collects:

1. **Vendor preset** (Panasonic Heishamon, generic, …) — pre-fills source
   entity-IDs to match that vendor's naming.
2. **Pump model** (J / K / L / T-CAP / M for Panasonic, or "other") —
   sets compressor, flow, and supply-temp thresholds.
3. **Source sensors** — review and override the auto-detected entity
   IDs. Anything you leave blank is treated as "this component is
   absent" (e.g. blank `dhw_temp` → no DHW card on the dashboard).
4. **Confirm** — finalize. The integration:
   - registers ~120 entities (sensors, advisors, helpers, controls)
   - deploys `<config>/packages/hph_efficiency.yaml` (utility_meter is
     the one piece of YAML that cannot be created via the Python API)
   - registers a Lovelace dashboard at **`/hph`**
   - copies SVG schematics to `<config>/www/hph/`

You can re-open the wizard any time via *Settings → Devices & Services →
HeatPump Hero → Configure* to change source mappings, vendor preset, or
electricity-cost settings.

## Step 5 — Open the dashboard

Navigate to **`/hph`** in your HA sidebar. You should see eight views
(Overview, Schematic, Analysis, Efficiency, Optimization, Programs,
Mobile, Configuration). Charts that need history will display a
"Sammele Daten — …" placeholder until enough samples have been recorded.

## Step 6 — (Optional) external sensors

See [external_sensors.md](external_sensors.md) — for example, a Shelly
power sensor as the electrical source, or an external heat meter as the
thermal source.

## Step 7 — (Optional) Grafana / InfluxDB

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
- HeatPump Hero reads and visualizes only — disable all `number.*` and
  `select.*` entities of the kamaradclimber integration in HA
  (Entity → Disable), and leave every `switch.hph_ctrl_*` off.

## Updating

In HACS → *Integrations* → *HeatPump Hero* → *Update* (visible when a new
release is available). After update, restart Home Assistant. Existing
configuration (vendor preset, source mappings, electricity price, etc.)
is preserved across updates — they live in the config entry, not in
mutable YAML files.

## Uninstalling

`Settings → Devices & Services → HeatPump Hero → ⋮ → Delete`. The
integration's `async_unload_entry` cleans up:

- the deployed `packages/hph_efficiency.yaml`
- the Lovelace dashboard registration
- the SVG assets in `www/hph/`
- all `sensor.hph_*` / `binary_sensor.hph_*` / helpers it registered

It does **not** touch the recorder DB, long-term statistics, HACS itself,
or any unrelated YAML files.

## Legacy: shell-installer (pre-v0.9)

The old `scripts/install.sh` flow that copied multiple `packages/*.yaml`
files into HA config is **deprecated** and will be removed in v1.0. Do
not use it for fresh installs. If you have an older v0.7/v0.8 install,
follow the migration notes in [CHANGELOG.md](../CHANGELOG.md).
