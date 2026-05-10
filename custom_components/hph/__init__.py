"""HeatPump Hero — Home Assistant custom integration.

Phase 3: fully self-contained Python integration.
  - Helper platforms (text/number/select/switch/datetime/button)
  - Template sensors and binary sensors
  - Python coordinators for every automation (no YAML automations deployed)
  - Minimal YAML bootstrap: dashboard + hph_efficiency.yaml only
  - Aggressive UI-uninstall cleanup
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue

from .bootstrap import (
    async_clean_deployed_files,
    async_deploy_yaml_packages,
    async_register_dashboard,
)
from .const import (
    COUNTER_HELPERS,
    DASHBOARD_URL_PATH,
    DATA_HASS_CONFIG,
    DATETIME_HELPERS,
    DOMAIN,
    NUMBER_HELPERS,
    PLATFORMS,
    SELECT_HELPERS,
    SWITCH_HELPERS,
    TEXT_HELPERS,
)

_LOGGER = logging.getLogger(__name__)


# Map of legacy entity_id → desired entity_id for the one-time rename.
# Triggered by name change in the deployed hph_efficiency.yaml package
# from "HeatPump Hero …" to "HPH …" — fresh installs already get the
# desired entity_id, but existing installs have the old slugified name
# baked into the entity registry.
_ENTITY_ID_MIGRATIONS = {
    "sensor.heatpump_hero_heating_limit_smoothed": "sensor.hph_heating_limit_smoothed",
    "sensor.heatpump_hero_spread_7_day_mean":      "sensor.hph_spread_7d_mean",
    "sensor.heatpump_hero_spread_7_day_stdev":     "sensor.hph_spread_7d_stdev",
    "sensor.heatpump_hero_dhw_fires_7_day_mean":   "sensor.hph_dhw_fires_7d_mean",
    "sensor.heatpump_hero_pressure_7_day_mean":    "sensor.hph_pressure_7d_mean",
    "sensor.heatpump_hero_indoor_deviation_smoothed": "sensor.hph_indoor_deviation_smoothed",
}


async def _migrate_entity_ids(hass: HomeAssistant) -> None:
    """Rename legacy 'heatpump_hero_*' entity_ids to 'hph_*' and
    consolidate the price-driven-DHW price helper into the cost-calc
    one. Both migrations are idempotent — safe on every startup."""
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    renamed = 0
    for old, new in _ENTITY_ID_MIGRATIONS.items():
        if registry.async_get(old) is None:
            continue  # not present (fresh install or already renamed)
        if registry.async_get(new) is not None:
            # Conflict: both old and new exist — drop the old (its
            # statistics are usually empty since the new name was
            # registered on a fresh restart).
            try:
                registry.async_remove(old)
                _LOGGER.info("hph migration: removed conflicting legacy entity %s", old)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("hph migration: cannot remove %s: %s", old, exc)
            continue
        try:
            registry.async_update_entity(old, new_entity_id=new)
            _LOGGER.info("hph migration: renamed %s → %s", old, new)
            renamed += 1
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("hph migration: rename %s → %s failed: %s", old, new, exc)
    if renamed:
        _LOGGER.info("hph migration: renamed %d legacy 'heatpump_hero_*' entities", renamed)

    # Consolidate the double price sensor: copy text.hph_ctrl_price_entity
    # value into text.hph_electricity_price_entity if the latter is empty.
    cost_ent = "text.hph_electricity_price_entity"
    ctrl_ent = "text.hph_ctrl_price_entity"
    cost_state = hass.states.get(cost_ent)
    ctrl_state = hass.states.get(ctrl_ent)
    if (cost_state is not None and ctrl_state is not None
            and not (cost_state.state or '').strip()
            and (ctrl_state.state or '').strip()
            and ctrl_state.state not in ('unknown', 'unavailable')):
        try:
            await hass.services.async_call(
                "text", "set_value",
                {"entity_id": cost_ent, "value": ctrl_state.state},
                blocking=True,
            )
            _LOGGER.info(
                "hph migration: copied price sensor %r from %s into %s",
                ctrl_state.state, ctrl_ent, cost_ent,
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("hph migration: price-sensor consolidation failed: %s", exc)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration domain key. Registers bridge services."""
    hass.data.setdefault(DOMAIN, {})

    # Bridge services: counter.increment / counter.reset equivalents for
    # Number entities (HA's counter platform services don't apply to Number).
    async def _counter_increment(call: Any) -> None:
        eid = call.data.get("entity_id")
        eids = eid if isinstance(eid, list) else ([eid] if eid else [])
        for e in eids:
            state = hass.states.get(e)
            if state is None:
                _LOGGER.debug("counter_increment: %s not found", e)
                continue
            try:
                cur = float(state.state)
            except (TypeError, ValueError):
                cur = 0.0
            await hass.services.async_call(
                "number", "set_value",
                {"entity_id": e, "value": cur + 1.0},
                blocking=False,
            )

    async def _counter_reset(call: Any) -> None:
        eid = call.data.get("entity_id")
        eids = eid if isinstance(eid, list) else ([eid] if eid else [])
        for e in eids:
            await hass.services.async_call(
                "number", "set_value",
                {"entity_id": e, "value": 0},
                blocking=False,
            )

    hass.services.async_register(DOMAIN, "counter_increment", _counter_increment)
    hass.services.async_register(DOMAIN, "counter_reset", _counter_reset)

    # export_now service — generates CSV from HA states; basic implementation.
    async def _export_now(call: Any) -> None:
        await _do_export(hass)

    hass.services.async_register(DOMAIN, "export_now", _export_now)

    async def _backup_config(call: Any) -> None:
        await _do_backup_config(hass)

    async def _restore_config(call: Any) -> None:
        await _do_restore_config(hass, call)

    hass.services.async_register(DOMAIN, "backup_config", _backup_config)
    hass.services.async_register(DOMAIN, "restore_config", _restore_config)

    # Recompute service — force HPH derived sensors to re-evaluate now,
    # without waiting for an upstream state change. Useful after source-
    # helper swap when heat pump is off.
    async def _recompute(_call: Any) -> None:
        targets = [
            "sensor.hph_thermal_power_active",
            "sensor.hph_electrical_power_active",
            "sensor.hph_thermal_power_runtime",
            "sensor.hph_electrical_power_runtime",
            "sensor.hph_thermal_energy_active",
            "sensor.hph_electrical_energy_active",
            "sensor.hph_cop_live",
            "sensor.hph_cop_daily",
            "sensor.hph_cop_monthly",
            "sensor.hph_scop",
            "sensor.hph_source_health",
            "sensor.hph_advisor_source_health",
            "sensor.hph_efficiency_trend",
        ]
        # update_entity service forces immediate re-evaluation of the
        # template sensor's state expression even when its tracked
        # entities haven't changed.
        try:
            await hass.services.async_call(
                "homeassistant", "update_entity",
                {"entity_id": targets},
                blocking=False,
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("hph.recompute failed: %s", exc)

    hass.services.async_register(DOMAIN, "recompute", _recompute)

    # run_legionella_now service — one-off legionella DHW boost.
    # 1. Sets DHW target to the configured legionella target temperature.
    # 2. Presses the force-DHW button (if available).
    async def _run_legionella_now(_call: Any) -> None:
        target_c_st = hass.states.get("number.hph_prog_legionella_target_c")
        target_c = float(target_c_st.state) if target_c_st and target_c_st.state not in (
            "unknown", "unavailable"
        ) else 65.0

        dhw_target_holder = hass.states.get("text.hph_ctrl_write_dhw_target")
        if dhw_target_holder and dhw_target_holder.state not in ("unknown", "unavailable", ""):
            dhw_eid = dhw_target_holder.state.strip()
            if dhw_eid:
                try:
                    await hass.services.async_call(
                        "number", "set_value",
                        {"entity_id": dhw_eid, "value": target_c},
                        blocking=False,
                    )
                    _LOGGER.info("hph.run_legionella_now: set %s → %.0f °C", dhw_eid, target_c)
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.warning("hph.run_legionella_now: set DHW target failed: %s", exc)

        force_dhw_holder = hass.states.get("text.hph_ctrl_write_force_dhw")
        if force_dhw_holder and force_dhw_holder.state not in ("unknown", "unavailable", ""):
            force_eid = force_dhw_holder.state.strip()
            if force_eid:
                try:
                    await hass.services.async_call(
                        "button", "press", {"entity_id": force_eid}, blocking=False,
                    )
                    _LOGGER.info("hph.run_legionella_now: pressed %s", force_eid)
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.warning("hph.run_legionella_now: press force-DHW failed: %s", exc)

    hass.services.async_register(DOMAIN, "run_legionella_now", _run_legionella_now)

    return True


_EXPORT_PREFIXES = ("sensor.hph_", "binary_sensor.hph_", "number.hph_")
_EXPORT_FORMATS = ("csv", "json", "xlsx")


def _discover_export_entities(hass: HomeAssistant) -> list[str]:
    """Discover all HPH state entities worth exporting.

    Excludes pure config helpers (text/select/switch/datetime/button — those
    are configuration, not telemetry) and the source-facade entities
    (`*hph_source_*`) which mirror upstream sensors already exported.
    """
    ids: list[str] = []
    for state in hass.states.async_all():
        eid = state.entity_id
        if not eid.startswith(_EXPORT_PREFIXES):
            continue
        if "hph_source_" in eid:
            continue
        ids.append(eid)
    return sorted(ids)


def _write_csv(path, rows: list[list[str]]) -> None:
    import csv
    with open(path, "w", encoding="utf-8", newline="") as fh:
        csv.writer(fh).writerows(rows)


def _write_json(path, rows: list[list[str]]) -> None:
    import json
    header, *data = rows
    payload = [dict(zip(header, r)) for r in data]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def _write_xlsx(path, rows: list[list[str]]) -> None:
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise RuntimeError(
            "xlsx export requires openpyxl — install it in HA Core "
            "(pip install openpyxl) or pick csv/json"
        ) from exc
    wb = Workbook()
    ws = wb.active
    ws.title = "HeatPump Hero"
    for r in rows:
        ws.append(r)
    wb.save(path)


async def _do_export(hass: HomeAssistant) -> None:
    """Write a snapshot of all HPH telemetry sensors to the configured path.

    Each scheduled run appends a new timestamped file, so the export
    directory accumulates a long-term archive over time.
    """
    from pathlib import Path
    from homeassistant.exceptions import HomeAssistantError
    from homeassistant.util import dt as dt_util

    now = dt_util.now()

    target_path_st = hass.states.get("text.hph_export_target_path")
    export_format_st = hass.states.get("select.hph_export_format")
    target_path = (
        target_path_st.state
        if target_path_st and target_path_st.state not in ("unknown", "unavailable", "")
        else hass.config.path("hph", "exports")
    )
    fmt = (
        export_format_st.state
        if export_format_st and export_format_st.state not in ("unknown", "unavailable", "")
        else "csv"
    ).lower()
    if fmt not in _EXPORT_FORMATS:
        _LOGGER.warning("HPH export: unknown format %r, falling back to csv", fmt)
        fmt = "csv"

    # Treat target as a directory unless it already has a file extension.
    # Each run produces a new timestamped file (long-term archive pattern).
    p = Path(target_path)
    if not p.suffix:
        ts_str = now.strftime("%Y-%m-%d_%H-%M-%S")
        p = p / f"hph_export_{ts_str}.{fmt}"
    target_path = str(p)

    entity_ids = _discover_export_entities(hass)
    rows: list[list[str]] = [["timestamp", "entity_id", "state", "unit", "friendly_name"]]
    ts = now.isoformat()
    for eid in entity_ids:
        st = hass.states.get(eid)
        if not st:
            continue
        unit = st.attributes.get("unit_of_measurement", "") or ""
        name = st.attributes.get("friendly_name", "") or ""
        rows.append([ts, eid, st.state, str(unit), str(name)])

    writer = {"csv": _write_csv, "json": _write_json, "xlsx": _write_xlsx}[fmt]

    def _do_write() -> None:
        p.parent.mkdir(parents=True, exist_ok=True)
        writer(p, rows)

    try:
        await hass.async_add_executor_job(_do_write)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.exception("HPH export failed: %s", exc)
        await hass.services.async_call(
            "persistent_notification", "create",
            {
                "notification_id": "hph_export_done",
                "title": "HeatPump Hero export — failed",
                "message": f"Export to {target_path} ({fmt}) failed: {exc}",
            },
            blocking=True,
        )
        raise HomeAssistantError(f"HPH export failed: {exc}") from exc

    await hass.services.async_call(
        "datetime", "set_value",
        {"entity_id": "datetime.hph_export_last_run", "datetime": now.isoformat()},
        blocking=True,
    )
    await hass.services.async_call(
        "persistent_notification", "create",
        {
            "notification_id": "hph_export_done",
            "title": "HeatPump Hero export",
            "message": f"Export written to {target_path} ({fmt}, {len(rows) - 1} entities).",
        },
        blocking=True,
    )
    _LOGGER.info(
        "HPH export written to %s (%s, %d entities)",
        target_path, fmt, len(rows) - 1,
    )


# ─── Backup / Restore ─────────────────────────────────────────────────────────

# Entity domains for each helper category.
_BACKUP_DOMAINS: dict[str, tuple[str, dict]] = {
    "number":   ("number",   {**NUMBER_HELPERS, **COUNTER_HELPERS}),
    "select":   ("select",   SELECT_HELPERS),
    "switch":   ("switch",   SWITCH_HELPERS),
    "text":     ("text",     TEXT_HELPERS),
    "datetime": ("datetime", DATETIME_HELPERS),
}

# Services that write a value back for each domain.
_RESTORE_SERVICE: dict[str, tuple[str, str]] = {
    "number":   ("number",   "set_value"),
    "select":   ("select",   "select_option"),
    "switch":   ("switch",   "turn_on"),      # special-cased below
    "text":     ("text",     "set_value"),
    "datetime": ("datetime", "set_value"),
}


async def _do_backup_config(hass: HomeAssistant) -> None:
    """Serialize all HPH helper states to a timestamped JSON file."""
    import json
    from pathlib import Path

    from homeassistant.util import dt as dt_util

    now = dt_util.now()
    snapshot: dict[str, Any] = {
        "hph_backup_version": 1,
        "timestamp": now.isoformat(),
        "entities": {},
    }

    for category, (domain, helpers) in _BACKUP_DOMAINS.items():
        for uid in helpers:
            entity_id = f"{domain}.{uid}"
            state = hass.states.get(entity_id)
            if state is None or state.state in ("unknown", "unavailable"):
                continue
            snapshot["entities"][entity_id] = state.state

    ts = now.strftime("%Y-%m-%d_%H-%M-%S")
    out_path = Path(hass.config.path("hph", f"config_backup_{ts}.json"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    await hass.async_add_executor_job(
        out_path.write_text, json.dumps(snapshot, indent=2, ensure_ascii=False), "utf-8"
    )
    _LOGGER.info("HPH config backup written to %s (%d entities)", out_path, len(snapshot["entities"]))
    await hass.services.async_call(
        "persistent_notification", "create",
        {
            "notification_id": "hph_backup_done",
            "title": "HeatPump Hero — config backup",
            "message": f"Backup written to `{out_path.relative_to(hass.config.path())}` "
                       f"({len(snapshot['entities'])} entities).",
        },
        blocking=True,
    )


async def _do_restore_config(hass: HomeAssistant, call: Any) -> None:
    """Restore HPH helper states from a backup JSON file."""
    import json
    from pathlib import Path

    file_path = call.data.get("file_path", "")
    if not file_path:
        _LOGGER.error("restore_config: file_path is required")
        return

    path = Path(file_path)
    if not path.is_absolute():
        path = Path(hass.config.path()) / path

    try:
        raw = await hass.async_add_executor_job(path.read_text, "utf-8")
        snapshot = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.error("restore_config: cannot read %s — %s", path, exc)
        return

    if snapshot.get("hph_backup_version") != 1:
        _LOGGER.warning("restore_config: unknown backup version, attempting anyway")

    entities: dict[str, str] = snapshot.get("entities", {})
    restored = 0
    skipped = 0

    for entity_id, value in entities.items():
        domain = entity_id.split(".")[0]
        svc_info = _RESTORE_SERVICE.get(domain)
        if svc_info is None:
            skipped += 1
            continue

        svc_domain, svc_name = svc_info
        try:
            if domain == "switch":
                svc_name = "turn_on" if value == "on" else "turn_off"
                await hass.services.async_call(
                    svc_domain, svc_name, {"entity_id": entity_id}, blocking=False
                )
            elif domain in ("number", "text", "datetime"):
                await hass.services.async_call(
                    svc_domain, svc_name,
                    {"entity_id": entity_id, "value": value},
                    blocking=False,
                )
            elif domain == "select":
                await hass.services.async_call(
                    svc_domain, svc_name,
                    {"entity_id": entity_id, "option": value},
                    blocking=False,
                )
            restored += 1
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("restore_config: could not restore %s = %r — %s", entity_id, value, exc)
            skipped += 1

    _LOGGER.info("HPH config restore done: %d restored, %d skipped", restored, skipped)
    await hass.services.async_call(
        "persistent_notification", "create",
        {
            "notification_id": "hph_restore_done",
            "title": "HeatPump Hero — config restore",
            "message": f"Restored {restored} entities from `{path.name}` ({skipped} skipped).",
        },
        blocking=True,
    )


async def _apply_sensor_config(hass: HomeAssistant, data: dict) -> None:
    """Seed source-mode selects and external entity text helpers from config-flow data."""
    # Determine thermal source mode from what the user picked in step 3.
    external_thermal_power = data.get("external_thermal_power", "")
    external_thermal_energy = data.get("external_thermal_energy", "")
    external_electrical_power = data.get("external_electrical_power", "")
    external_electrical_energy = data.get("external_electrical_energy", "")

    if external_thermal_energy:
        thermal_mode = "external_energy"
    elif external_thermal_power:
        thermal_mode = "external_power"
    else:
        thermal_mode = None  # keep whatever the entity has (default: calculated)

    if external_electrical_energy:
        electrical_mode = "external_energy"
    elif external_electrical_power:
        electrical_mode = "external_power"
    else:
        electrical_mode = None  # keep default (heat_pump_internal)

    if thermal_mode:
        await hass.services.async_call(
            "select", "select_option",
            {"entity_id": "select.hph_thermal_source", "option": thermal_mode},
            blocking=False,
        )

    if electrical_mode:
        await hass.services.async_call(
            "select", "select_option",
            {"entity_id": "select.hph_electrical_source", "option": electrical_mode},
            blocking=False,
        )

    # Seed all entity-ID text helpers from config/options flow data.
    _text_map = {
        "text.hph_src_external_thermal_power": external_thermal_power,
        "text.hph_src_external_thermal_energy": external_thermal_energy,
        "text.hph_src_external_electrical_power": external_electrical_power,
        "text.hph_src_external_electrical_energy": external_electrical_energy,
        "text.hph_indoor_temp_entity": data.get("indoor_temp_entity", ""),
        "text.hph_outdoor_temp_override_entity": data.get("outdoor_temp_entity", ""),
        # Unified electricity-price helper — used by both cost calc
        # and price-driven DHW. Setup-flow legacy key 'ctrl_price_entity'
        # falls back into the same helper if the dedicated cost-calc key
        # wasn't filled.
        "text.hph_electricity_price_entity":
            data.get("electricity_price_entity") or data.get("ctrl_price_entity", ""),
        "text.hph_ctrl_pv_surplus_entity": data.get("ctrl_pv_surplus_entity", ""),
        "text.hph_ctrl_forecast_entity": data.get("ctrl_forecast_entity", ""),
    }
    for entity_id, value in _text_map.items():
        if value:
            await hass.services.async_call(
                "text", "set_value",
                {"entity_id": entity_id, "value": value},
                blocking=False,
            )


# (card_name, url_substring, hacs_repo, fs_fallback_path)
# url_substring is matched against registered Lovelace resource URLs.
# fs_fallback_path is checked against <config>/www/community/ if the
# resource store is not accessible.
_REQUIRED_FRONTEND_CARDS = [
    ("mushroom",        "lovelace-mushroom/mushroom",           "piitaya/lovelace-mushroom",          "www/community/lovelace-mushroom/mushroom.js"),
    ("apexcharts-card", "apexcharts-card/apexcharts-card",     "RomRider/apexcharts-card",            "www/community/apexcharts-card/apexcharts-card.js"),
    ("bubble-card",     "Bubble-Card/bubble-card",             "Clooos/Bubble-Card",                  "www/community/Bubble-Card/bubble-card.js"),
    ("button-card",     "button-card/button-card",             "custom-cards/button-card",            "www/community/button-card/button-card.js"),
    ("auto-entities",   "lovelace-auto-entities/auto-entities","thomasloven/lovelace-auto-entities",  "www/community/lovelace-auto-entities/auto-entities.js"),
    ("card-mod",        "lovelace-card-mod/card-mod",          "thomasloven/lovelace-card-mod",       "www/community/lovelace-card-mod/card-mod.js"),
]

# Vendor presets that map to a specific HA integration domain we can check.
_VENDOR_INTEGRATION_MAP: dict[str, str] = {
    "panasonic_heishamon": "panasonic_heishamon",
}


def _missing_cards_from_filesystem(config_dir_path: str, cards: list) -> list[tuple[str, str, str]]:
    """Filesystem fallback: check www/community/ paths."""
    from pathlib import Path
    config_dir = Path(config_dir_path)
    return [
        (name, url_sub, repo)
        for name, url_sub, repo, fs_path in cards
        if not (config_dir / fs_path).exists()
    ]


async def _async_check_prerequisites(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Create HA Repairs issues for missing frontend cards and vendor integrations."""
    # Prefer the Lovelace resource store (same source as Settings → Dashboards → Resources).
    missing_cards: list[tuple[str, str, str]] = []
    lovelace_resources = hass.data.get("lovelace_resources")
    if lovelace_resources is not None:
        try:
            registered_urls: list[str] = [
                item.get("url", "") for item in lovelace_resources.async_items()
            ]
            for card_name, url_sub, hacs_repo, _fs in _REQUIRED_FRONTEND_CARDS:
                if not any(url_sub in url for url in registered_urls):
                    missing_cards.append((card_name, url_sub, hacs_repo))
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Could not read Lovelace resource store, falling back to filesystem: %s", exc)
            missing_cards = await hass.async_add_executor_job(
                _missing_cards_from_filesystem, hass.config.path(), _REQUIRED_FRONTEND_CARDS
            )
    else:
        missing_cards = await hass.async_add_executor_job(
            _missing_cards_from_filesystem, hass.config.path(), _REQUIRED_FRONTEND_CARDS
        )

    for card_name, _url_sub, hacs_repo in missing_cards:
        async_create_issue(
            hass,
            DOMAIN,
            f"missing_frontend_card_{card_name.replace('-', '_')}",
            is_fixable=False,
            severity=IssueSeverity.WARNING,
            translation_key="missing_frontend_card",
            translation_placeholders={"card_name": card_name, "hacs_repo": hacs_repo},
            learn_more_url="https://hacs.xyz/",
        )

    # Check vendor integration.
    vendor = entry.data.get("vendor_preset", "")
    integration_domain = _VENDOR_INTEGRATION_MAP.get(vendor)
    if integration_domain and integration_domain not in hass.config.components:
        async_create_issue(
            hass,
            DOMAIN,
            f"missing_vendor_integration_{integration_domain}",
            is_fixable=False,
            severity=IssueSeverity.ERROR,
            translation_key="missing_vendor_integration",
            translation_placeholders={"vendor": vendor},
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HeatPump Hero from a config entry."""
    _LOGGER.info("Setting up HeatPump Hero entry %s", entry.entry_id)

    hass.data.setdefault(DOMAIN, {})
    # Merge options (written by the reconfigure flow) on top of the initial
    # install data so that reconfiguring via the Configure button doesn't lose
    # anything. Options always win over initial data for the same key.
    merged = {**entry.data, **entry.options}
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_HASS_CONFIG: hass.config.path(),
        "options": dict(entry.options) if entry.options else {},
        "data": merged,
    }

    # Deploy dashboard + efficiency package; migrate old automation packages.
    deployed = await async_deploy_yaml_packages(hass)
    hass.data[DOMAIN][entry.entry_id]["bootstrap"] = deployed

    # One-time migration: rename platform:statistics entities created by
    # earlier rc4 versions with name "HeatPump Hero …" → entity_id
    # sensor.heatpump_hero_* over to sensor.hph_* for naming consistency.
    # Also unifies the price-driven-DHW helper text.hph_ctrl_price_entity
    # into text.hph_electricity_price_entity (the cost-calc helper).
    await _migrate_entity_ids(hass)

    # Forward to platforms (text/number/select/switch/datetime/button/sensor/binary_sensor).
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Auto-register the dashboard (idempotent).
    try:
        await async_register_dashboard(hass)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("Dashboard auto-registration failed: %s", exc)

    # Surface missing prerequisites as HA Repairs entries.
    hass.async_create_task(_async_check_prerequisites(hass, entry))

    # Apply chosen vendor preset (one-shot on first install).
    preset = merged.get("vendor_preset")
    if preset and preset != "keep_current":
        from .helpers.vendor_apply import async_apply_vendor_preset, async_apply_pump_model
        await async_apply_vendor_preset(hass, preset)
        # Mirror the preset selection in the select entity.
        await hass.services.async_call(
            "select", "select_option",
            {"entity_id": "select.hph_vendor_preset", "option": preset},
            blocking=False,
        )
    else:
        from .helpers.vendor_apply import async_apply_pump_model

    # Apply chosen pump model thresholds (also updates select.hph_pump_model).
    model = merged.get("pump_model")
    if model:
        await async_apply_pump_model(hass, model)

    # Apply step-3 external sensor config from config flow (merged data).
    await _apply_sensor_config(hass, merged)

    # Start coordinators (automation logic).
    from .coordinators import (
        advisor,
        bridge,
        control,
        control_ext,
        cycles,
        diagnostics,
        efficiency,
        export,
        models,
        programs,
        runtime_kwh,
    )

    all_unsubs: list = []
    for coord in [cycles, advisor, diagnostics, control, control_ext, programs, bridge, export, efficiency, models, runtime_kwh]:
        try:
            unsubs = await coord.async_setup(hass, entry)
            all_unsubs.extend(unsubs)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Coordinator %s failed to start: %s", coord.__name__, exc)

    hass.data[DOMAIN][entry.entry_id]["coordinator_unsubs"] = all_unsubs

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload entry — stop coordinators, unload platforms."""
    # Stop coordinator listeners
    for unsub in hass.data[DOMAIN].get(entry.entry_id, {}).get("coordinator_unsubs", []):
        try:
            unsub()
        except Exception:  # noqa: BLE001
            pass

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Aggressive cleanup on UI-uninstall: remove every file we wrote."""
    _LOGGER.info("Removing HeatPump Hero — file cleanup begins")
    await async_clean_deployed_files(hass)
    _LOGGER.info("HeatPump Hero removed cleanly")
