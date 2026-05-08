# HeishaHub

Komplett-Paket für **Heishamon** in Home Assistant: Dashboard im Layout des
Heishamon-Web-UIs, Service-Cloud-ähnliche Auswertegraphen, Anlagen-Schema und
Langzeit-Effizienz (JAZ / MAZ / TAZ / COP) — universal, plug-and-play, mit
optionaler InfluxDB-/Grafana-Integration für Mehrjahresvergleich.

## Features

- Übersichts-Dashboard (Mushroom) im Look des Heishamon-Web-UIs
- Anlagen-Schema als Bubble-Card mit SVG + Live-Hotspots
- ApexCharts-Auswertung mit Mehrachsen, Zeitspannen-Picker, Serien-Toggle
- JAZ / MAZ / TAZ / Live-COP für Heizen, Warmwasser, Kühlen
- Externe Sensoren (Shelly Pro 3EM / 1PM / EM, MQTT-Wärmemengenzähler) per
  UI-Dropdown integrierbar — kein YAML-Edit
- Auto-Hide für nicht vorhandene Komponenten (HK2, DHW, Puffer, Solar, Pool)
- Optional: Grafana-Boards für Mehrjahres-JAZ/MAZ-Vergleich

## Installation

Siehe [docs/installation.md](docs/installation.md).

## Abhängigkeiten

- [kamaradclimber/heishamon-homeassistant](https://github.com/kamaradclimber/heishamon-homeassistant)
- [RomRider/apexcharts-card](https://github.com/RomRider/apexcharts-card)
- [Clooos/Bubble-Card](https://github.com/Clooos/Bubble-Card)
- [piitaya/lovelace-mushroom](https://github.com/piitaya/lovelace-mushroom)
- [custom-cards/button-card](https://github.com/custom-cards/button-card)
- [thomasloven/lovelace-auto-entities](https://github.com/thomasloven/lovelace-auto-entities)
- [thomasloven/lovelace-card-mod](https://github.com/thomasloven/lovelace-card-mod)
