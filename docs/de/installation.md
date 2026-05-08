# Installation

🌐 [English](../installation.md) · Deutsch (diese Datei)


## Voraussetzungen

| Komponente | Mindestversion | Quelle |
|---|---|---|
| Home Assistant | 2025.4 | hass |
| HACS | 2.0 | https://hacs.xyz |
| MQTT-Broker | beliebig | z. B. Mosquitto-Add-on |
| Heishamon-Hardware | aktuelle Egyras/IgorYbema-Firmware | https://github.com/Egyras/HeishaMon |

Optional für Langzeit-Statistik:
- InfluxDB-Add-on
- Grafana-Add-on

## Schritt 1 — Heishamon-Integration installieren

In HACS:

1. *Integrations* → ⋮ → *Custom repositories*
2. URL: `https://github.com/kamaradclimber/heishamon-homeassistant`
3. Kategorie: *Integration*
4. *Heishamon* installieren, Home Assistant neu starten.
5. Settings → Devices & Services → MQTT-Auto-Discovery sollte die WP finden.
   Topic-Prefix prüfen (Default: `panasonic_heat_pump`).

## Schritt 2 — Frontend-Plugins installieren

In HACS *Frontend* nacheinander suchen und installieren:

- ApexCharts Card
- Bubble Card
- Mushroom
- button-card
- auto-entities
- card-mod

## Schritt 3 — HeishaHub-Repo holen

```bash
cd /tmp
git clone https://github.com/st03psn/heishahub.git
```

## Schritt 4 — Installer ausführen (empfohlen)

```bash
cd heishahub
./scripts/install.sh /path/to/your/homeassistant/config
```

Der Installer kopiert:
- `packages/*.yaml` → `<config>/packages/`
- `dashboards/heishahub.yaml` → `<config>/heishahub/dashboard.yaml`
- `dashboards/assets/*.svg` → `<config>/www/heishahub/`
- `blueprints/heishahub_setup.yaml` → `<config>/blueprints/script/heishahub/`

und ergänzt `homeassistant: packages: !include_dir_named packages` in
`configuration.yaml` (idempotent).

### Manuelle Installation (Alternative)

Wer keinen Shell-Zugriff hat: Inhalt der vier Verzeichnisse manuell kopieren
(z. B. via *File Editor*-Add-on) und obige Zeile in `configuration.yaml`
einfügen.

## Schritt 5 — Home Assistant neu starten

`Settings → System → Restart`. Nach dem Neustart in *Developer Tools → States*
nach `heishahub_` filtern — die HeishaHub-Sensoren sollten erscheinen.

## Schritt 6 — Setup-Blueprint ausführen

`Settings → Automations & Scenes → Blueprints` → *HeishaHub Setup* → 
*Skript erstellen* → Ausführen. Liefert eine persistente Notification mit
einer Diagnose, ob die Heishamon-Entities gefunden wurden.

## Schritt 7 — Dashboard hinzufügen

`Settings → Dashboards → Add Dashboard → From YAML` →

```yaml
title: HeishaHub
icon: mdi:heat-pump
mode: yaml
filename: heishahub/dashboard.yaml
```

## Schritt 8 — (Optional) Externe Sensoren

Siehe [external_sensors.md](external_sensors.md).

## Schritt 9 — (Optional) Grafana / InfluxDB

1. **InfluxDB-Add-on** installieren, Bucket `heishahub` anlegen, Token erzeugen.
2. **HA InfluxDB-Integration** konfigurieren → spiegelt alle `sensor.heishahub_*`
   nach InfluxDB.
3. Alternativ **Telegraf** mit der Config aus
   `grafana/telegraf_mqtt.conf` für direkten MQTT→InfluxDB-Pfad
   (höhere Auflösung, kein HA-Recorder-Limit).
4. **Grafana-Add-on** starten, InfluxDB-Datasource hinzufügen, Dashboards aus
   `grafana/overview.json` und `grafana/efficiency_jaz_maz.json` importieren.

## Koexistenz mit HeishaMoNR (Node-Red)

Beide Systeme können parallel am MQTT-Broker hören. **Schreibend** sollte nur
eines aktiv sein. Empfehlung während Parallel-Test:

- HeishaMoNR steuert (Schedules, CCC, RTC, SoftStart),
- HeishaHub liest und visualisiert nur — alle `number.*` und `select.*` aus
  der kamaradclimber-Integration in HA deaktivieren (Entity → Disable).

## Update

```bash
cd /tmp/heishahub
git pull
./scripts/install.sh /path/to/your/homeassistant/config
```

Bestehende Helper-Werte (Quellen-Auswahl, externe Entity-IDs) bleiben erhalten,
da der Installer die `input_*`-Entities nicht zurücksetzt.
