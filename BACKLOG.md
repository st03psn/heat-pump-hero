# HeatPump Hero — Backlog

Items that are scoped but not yet scheduled for a specific release.
Priority roughly top-to-bottom within each section.

For the full release history see [CHANGELOG.md](CHANGELOG.md).
For the macro roadmap see [docs/roadmap.md](docs/roadmap.md).

---

## 🔴 High priority — finish v0.9.0 stable

### Dashboard polish

- **Efficiency tab: DHW-direct COP tiles** — add
  `sensor.hph_cop_monthly_dhw_direct` / `hph_cop_yearly_dhw_direct` tiles
  once they have accumulated one full month of data on the reference install.
  Guards: `state_not 0` + availability check on `hph_source_dhw_power_thermal`.

- **COP by mode on Efficiency view** — per-mode COP cards
  (`sensor.hph_cop_monthly_heating`, `_monthly_dhw`) with conditional show
  when tariff-split is enabled.

- **View consolidation** — "COP last 30 days" lives in both Overview and
  Analysis. Move the 30-day view exclusively to Efficiency; replace in
  Overview/Analysis with a 7-day or 14-day chart to reduce visual duplication.

- **Zone 2 climate card UX** (Control tab Section 3) — the card currently
  shows `text.hph_ctrl_write_z2_climate` directly without an empty-state
  check. Needs either a `conditional: state_not ""` wrapper or a smarter
  template that gracefully shows "not configured" when the helper is blank.

### Entities & presets

- **`panasonic_heishamon_aquarea` preset — add all rc6 additions.** The
  `panasonic_heishamon_aquarea` (HeishaMon MQTT with `aquarea_*` prefix)
  preset is missing the ~25 entries added in PRs B/C/D for monitoring
  sensors, Optional PCB, restart button, S0-Watt. Mirror every new
  `hph_src_*` / `hph_ctrl_write_*` key from `panasonic_heishamon` with the
  `aquarea_main_` prefix equivalent.

- **`hph_src_s0_power` initial value correction.** The TEXT_HELPER has
  `"initial": ""` but the panasonic_heishamon preset fills it with
  `sensor.panasonic_heat_pump_s0_watt`. The initial value in TEXT_HELPERS
  should match the preset for consistency (or stay blank and rely on preset
  only — pick one, document). Currently `test_const_consistency()` passes
  because the rule only fires when initial is non-empty.

### Integration hygiene

- **GitHub Release tag.** Create annotated tag `v0.9.0-rc6` and push it so
  HACS shows update notifications to users on rc5 or earlier.
  ```
  git tag -a v0.9.0-rc6 -m "v0.9.0-rc6"
  git push origin v0.9.0-rc6
  ```

- **Recorder exclusions.** Identify intermediate/instantaneous sensors that
  should not go into HA long-term statistics (standby power, live COP,
  thermal power, compressor freq runtime copies) and exclude them from the
  recorder to reduce DB growth. Use `_async_exclude_from_recorder()` pattern
  **only after verifying it does not corrupt the DB** (see the 2026-05-18
  incident in memory `feedback_no_db_writes.md`). Safer alternative:
  add `recorder: exclude:` block in `hph_efficiency.yaml`.

---

## 🟡 Medium priority — v0.9.x polish

### UX improvements

- **OptionsFlow entity-pickers.** Replace `text.hph_src_*` plain text-boxes
  in the config wizard with HA-native entity-selector pickers. This
  requires HA `selector.entity` support in config-flow, available since
  HA 2023.9. Benefit: validates entity existence before saving;
  auto-suggest matching sensors.

- **COP-live transparency.** Alongside the live COP value, show
  `thermal_power_active / electrical_power_active` as the underlying
  ratio — e.g. "COP 3.2 (4 800 W / 1 500 W)". Either as the hero-card
  secondary text or a tooltip chip.

- **Demo mode.** `switch.hph_demo_mode` + `hph.demo_seed_history` service
  injects 13 months of synthetic statistics (realistic seasonal curve,
  DHW cycles, one fault event) so all dashboard views can be demonstrated
  without a real heat pump or recorder history.

### Testing & CI

- **pytest-based test suite** mocking HA core. Target: `pytest-homeassistant-
  custom-component`, HA 2025.4+. Scenarios: config flow wizard all steps,
  preset apply + capability gating, CTRL_FACADE proxy read/write, coordinator
  cycle start/stop, export service, bootstrap deploy/clean.

- **Per-platform translations** `translations/{en,de,nl}.json` for all
  config-flow strings, entity names, and service descriptions. `en.json`
  already exists; `de.json` is the priority (primary user base).

---

## 🟢 Low priority — pre-v1.0

### Vendor expansion

- **`panasonic_heishamon_aquarea` preset completion** (see High priority above
  — move here once the rc6 gap is filled and the focus shifts to new vendors).

- **Luxtronik generic preset.** Covers ~8 German OEM brands (Bosch,
  Buderus, Junkers, Wolf, …) that use the same Luxtronik controller.
  Prerequisite: `option_map` field in CTRL_FACADES for enum translation
  (vendor option strings differ from HPH's generic "Heat / Cool / DHW").

- **Mitsubishi Ecodan / MELCloud preset.** MELCloud HA integration entity IDs
  documented; needs `climate-splitter` helper to fan out the single
  `climate.*` entity into HPH source helpers.

- **Daikin Altherma 3 preset completion.** Current `daikin_altherma_core`
  has only 5 entries. Expand with `leaving_water_temperature`,
  `heating_consumed_energy`, and control write targets using the
  `daikin_residential_altherma` integration entity IDs.

### Dashboard

- **HACS-default-repository submission.** Requires stable release, full
  CI passing, no known critical bugs. Prerequisite: v1.0.0 tag.

- **PV self-consumption net cost sensor** `sensor.hph_cost_today_net` —
  subtracts PV-covered kWh (at feed-in tariff) from gross cost. Needs
  `text.hph_pv_feed_in_entity` + a new `number.hph_feed_in_price_ct_per_kwh`
  helper.

- **Weather-source adapter.** Swappable weather providers (DWD /
  OpenWeatherMap / Met.no / local weather station). Adds
  `sensor.hph_scop_weather_adjusted` which normalises SCOP by heating
  degree-days. DWD recipe `docs/weather/dwd.md` is priority for DE users.

---

## 🔵 Ideas (post-v1.0, not yet scoped)

- **Per-mode long-term statistics with multi-year overlay charts.** Persistent
  LTS for thermal + electrical kWh AND COP split by mode, browseable across
  years from the dashboard. Existing primitives exist; missing UI + reliability
  story for mode-split vs. external Shelly total.

- **Drop-in advisor extension API.** `<config>/hph/advisors/*.py`
  auto-discovered on startup — allows power-users to add custom advisor
  sensors without modifying the integration.

- **Optional defrost-forecast advisor.** RH + outdoor T° → icing likelihood
  heuristic; recommends pre-emptive defrosts or flags unexpected defrost
  frequency.

- **Efficiency-drift weather-adjustment.** `sensor.hph_scop_weather_adjusted`
  via heating-degree-day normalisation — makes year-over-year SCOP comparisons
  fair when one winter was colder than another.

- **Standalone script installer removal.** `scripts/install.sh` and
  `scripts/update.ps1` are kept for v0.8 migration compatibility. Remove
  in v1.0 once all users have migrated to HACS.

---

## ✅ Recently completed (reference)

| Item | Release |
|---|---|
| CTRL_FACADE typed proxy entities — full HAL | rc5 |
| Model capability map + vendor-filtered dropdown | rc5 |
| 14 monitoring facades (PR B) | rc6 |
| Optional PCB + HeishaMon restart (PR C) | rc6 |
| DHW COP direct + S0-Watt (PR C) | rc6 |
| Konfigurationsfehler fix — conditional wrappers | rc6 |
| Config tab completeness + vendor-generic heating curve | rc6 |
| `test_const_consistency()` smoke test | rc6 |
| Auto-install Lovelace frontend cards via HACS | rc5 |
| Vendor-integration repair timing fix | rc6 |
| Standby breakdown fix (Stage A utility_meter, Stage B runtime_kwh) | rc5 |
