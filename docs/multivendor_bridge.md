# Multi-platform read-only bridge (v0.7.2)

HeatPump Hero is a Home Assistant package — but the **derived metrics**
it computes (COP, SCOP, advisor states, diagnostics) are useful to
anyone, regardless of which home-automation platform they use day to
day. The bridge republishes a curated set of `sensor.hph_*` back onto
MQTT so ioBroker, openHAB, Node-RED, Domoticz, or a secondary HA
instance can subscribe.

**Scope:** read-only. Control extensions stay HA-exclusive — the write
paths target vendor-specific entities that are not portable.

## What you get

| Topic | Example payload |
|---|---|
| `hph/sensor/hph_cop_daily/state` | `4.32` |
| `hph/sensor/hph_cop_daily/attributes` | `{"unit_of_measurement":"x","friendly_name":"…", …}` |
| `hph/sensor/hph_advisor_summary/state` | `warn` |
| `hph/sensor/hph_advisor_summary/attributes` | `{"message":"Short cycling above threshold", "metric":12, …}` |
| `hph/sensor/hph_diagnostics_current_error/state` | `H62` |
| `hph/sensor/hph_diagnostics_current_error/attributes` | `{"severity":"critical","message":"Water flow low",…}` |
| `hph/binary_sensor/hph_compressor_running/state` | `on` |

Default prefix is `hph` and configurable via
`input_text.hph_bridge_prefix`.

All publishes use `retain=true`, so subscribers connecting later see
the latest snapshot immediately. Disabling the bridge sends empty
retained payloads to clear all topics at the broker.

## Hardware-abstraction guarantee

The bridge republishes only `sensor.hph_*` (computed sensors), never
`panasonic_heat_pump_*` or any other vendor's raw entities. Topic
names are stable across:

- Heat-pump swap (Heishamon → Daikin Altherma → Vaillant mypyllant)
- Integration swap (kamaradclimber → custom MQTT → vendor cloud)

Only the ~17 `input_text.hph_src_*` source-helpers in HA need
reconfiguration after a swap; everything downstream — including this
bridge — keeps working without YAML edits.

For the Heishamon raw values (inlet temperature, flow, etc.),
subscribe to the Heishamon MQTT topics directly. Those are already
plain `panasonic_heat_pump/main/Inlet_Temp/state` and similar, so
republishing them through this bridge would be redundant.

## Prerequisites

1. An MQTT broker reachable from HA. The Mosquitto add-on is fine; an
   external broker works too.
2. The HA `mqtt:` integration is configured and connected.
3. Heishamon and HPH-Bridge can share the same broker.

## Setup

1. Open the **Configuration** view in the HPH dashboard.
2. Find the **Multi-platform bridge (read-only)** section.
3. Set a topic prefix (default `hph` is fine for most installs; pick
   something like `house1/hph` if you run multiple heat pumps on one
   broker).
4. Toggle **HeatPump Hero — multi-platform bridge** on.
5. The initial snapshot is published within ~1 second; a persistent
   notification confirms.

## Verifying with `mosquitto_sub`

```bash
mosquitto_sub -h <broker-host> -t 'hph/#' -v
```

You should see ~50 entries appear in the first second, then live
updates as values change.

## Recipe — ioBroker

1. In ioBroker Admin, install **MQTT Client/Broker** adapter
   (`iobroker.mqtt`).
2. Configure the adapter:
   - Type: **Subscribe to states from broker (Client/Subscriber)**
   - URL: `mqtt://<broker-host>:1883`
   - Username/password as configured in your broker
   - **Subscribe patterns:** `hph/#`
3. Save and start.
4. Open **Objects** → look under `mqtt.0.hph.*`. Each topic becomes a
   state object automatically. Numeric strings are parsed as numbers;
   the `attributes` topics stay as JSON strings (parse with a JS
   adapter / Blockly script if needed).

## Recipe — openHAB

1. Install the **MQTT Binding** add-on.
2. Add an MQTT Broker Thing pointing at your broker.
3. Add a **Generic MQTT Thing** as a child:

   ```text
   Thing mqtt:topic:hph "HeatPump Hero" (mqtt:broker:mybroker) {
     Channels:
       Type number : copDaily       "COP — daily"        [ stateTopic="hph/sensor/hph_cop_daily/state" ]
       Type number : copMonthly     "COP — monthly"      [ stateTopic="hph/sensor/hph_cop_monthly/state" ]
       Type number : scop           "SCOP"               [ stateTopic="hph/sensor/hph_scop/state" ]
       Type string : advisorSummary "Advisor — summary"  [ stateTopic="hph/sensor/hph_advisor_summary/state" ]
       Type string : faultCode      "Fault code"         [ stateTopic="hph/sensor/hph_diagnostics_current_error/state" ]
       Type contact : compressor    "Compressor running" [ stateTopic="hph/binary_sensor/hph_compressor_running/state",
                                                          on="on", off="off" ]
   }
   ```

4. Link the channels to Items as usual.

## Recipe — Node-RED

1. Add an **mqtt-in** node:
   - Server: your broker
   - Topic: `hph/+/+/state`
   - Output: a parsed JSON object (or auto-detect)
2. The `msg.topic` carries the entity, `msg.payload` the value.
3. For attribute access, use a second `mqtt-in` on `hph/+/+/attributes`
   and `JSON.parse` the payload.

Example flow snippet (function node):

```javascript
const parts = msg.topic.split('/');     // ["hph","sensor","hph_cop_daily","state"]
const entity = parts[1] + '.' + parts[2];
msg.entity = entity;
return msg;
```

## Recipe — secondary HA instance

The bridge does **not** publish HA Discovery payloads in v0.7.2 (it
targets non-HA platforms primarily). To consume on a secondary HA, add
manual `mqtt sensor:` entries pointing at the topics. HA-Discovery
support is on the roadmap if there is demand.

## Limitations

- **Read-only.** Setting values on these topics from another platform
  has no effect on HA. Control automations remain HA-exclusive.
- **Whitelist is hardcoded.** Adding an entity = edit
  `packages/hph_bridge.yaml` (see below) and reload. Programmatic
  enumeration is intentionally out of scope.
- **Disable clears retained topics.** If you re-enable the bridge,
  the initial-publish automation refills them. Subscribers see a
  brief gap, then current values.
- **No QoS guarantees.** Default QoS 0 — fine for monitoring; not for
  audit-grade event logs.
- **No HA Discovery.** Other HA instances need manual sensor configs
  (see above).

## Adding an entity to the whitelist

`packages/hph_bridge.yaml` keeps the entity list in two synced places:

1. The `entity_id:` block of the `hph_bridge_publish_state` automation
   trigger — drives live updates.
2. The `variables.entities` block of the `hph_bridge_iterate` script —
   drives initial-publish and clear-on-disable.

Add the new entity to **both** lists. After saving, in HA: **Developer
Tools → YAML → Reload Automations** and **Reload Scripts**. Toggle the
bridge off and on once to push the new value.

## Forward-looking

v0.8 will add a weather-source-adapter package and a witterungs-adjusted
SCOP sensor (`sensor.hph_scop_weather_adjusted`). Once available, those
new derived sensors will be added to the bridge whitelist in a small
patch — no architectural changes.
