# Roadmap

🌐 English (this file) · [Deutsch](de/roadmap.md)

## v0.1 — skeleton (current)

- [x] Repository structure, HACS manifest, MIT license
- [x] Packages: core / external / efficiency / cycles / advisor / control
- [x] Dashboard with 6 views (Overview, Schema, Analysis, Efficiency,
  Optimization, Configuration)
- [x] Setup blueprint (diagnostic)
- [x] CLI installer `scripts/install.sh`
- [x] Grafana skeletons (overview, efficiency_jaz_maz)
- [x] Telegraf MQTT bridge config
- [x] CI: yamllint, JSON validation, HACS action
- [x] Docs: installation, external_sensors, optimization, tweaking, roadmap
- [x] Bilingual docs (English primary, German secondary)

## v0.2 — first usable release

- [ ] Bubble-Card SVG schematic with live hotspots (replacing the markdown
  placeholder)
- [ ] Schematic variants for HK1+DHW, HK1+HK2+DHW, +buffer
- [ ] Topic prefix as a single variable (`secrets.yaml` entry)
- [ ] Tariff splits in `utility_meter` (heating/dhw/cooling separate)
- [ ] HA Energy-Dashboard integration as "individual devices"
- [ ] Mobile-optimized dashboard layout
- [ ] Screenshots in `docs/screenshots/`

## v0.3 — statistics & long-term

- [ ] Weekly / monthly / yearly heatmap (outdoor × hour × COP)
- [ ] Grafana dashboards with real queries (today only skeletons)
- [ ] Document the InfluxDB schema, provide example queries
- [ ] Auto-detect heating-limit temperature
- [ ] Year-over-year comparison (Apex comparator)

## v0.4 — advisor extensions

- [ ] Heating-curve recommendation derived from data (target vs. actual
  supply over outdoor temperature, linear regression)
- [ ] Pump curve recommendation (spread histogram)
- [ ] Water-pressure trend detection (slow leak)
- [ ] Efficiency-drift detection (last year vs. current, weather-adjusted)
- [ ] DHW timing recommendation (based on usage pattern)

## v0.5 — control extensions

- [ ] Adaptive heating curve (self-learning from indoor sensors)
- [ ] Price-driven DHW (Tibber / aWATTar integration)
- [ ] Configurable legionella program
- [ ] Weather forecast pre-heating
- [ ] Screed dry-out program (for new builds)

## v1.0 — stable & documented

- [ ] Full test suite (HA CI with mocked MQTT)
- [ ] Internationalization (EN, NL — typical Heishamon communities)
- [ ] Video walkthrough
- [ ] Submission to the HACS default repository
- [ ] Zone 2 / buffer / solar / pool fully tested with beta users

## Out of scope

- A dedicated Python custom integration (kamaradclimber covers entities — no
  need to duplicate work).
- Cloud features (HeishaHub stays 100 % local).
- Standalone control without the kamaradclimber integration (too much
  abstraction work for too little value).

## Contributing

Issues with concrete use-cases very welcome. Before opening a PR, please
read the design principles in [CLAUDE.md](../CLAUDE.md), in particular the
universality, advisor schema, and control-switch conventions.
