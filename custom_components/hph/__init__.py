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

    return True


async def _do_export(hass: HomeAssistant) -> None:
    """Write a CSV snapshot of key HPH sensors to the configured path."""
    import csv
    import io
    from pathlib import Path

    target_path_st = hass.states.get("text.hph_export_target_path")
    export_format_st = hass.states.get("select.hph_export_format")
    target_path = (
        target_path_st.state
        if target_path_st and target_path_st.state not in ("unknown", "unavailable", "")
        else hass.config.path("www", "hph_export.csv")
    )
    fmt = (
        export_format_st.state
        if export_format_st and export_format_st.state not in ("unknown", "unavailable", "")
        else "csv"
    )

    from homeassistant.util import dt as dt_util
    now = dt_util.now()

    sensor_ids = [
        "sensor.hph_cop_live",
        "sensor.hph_cop_daily",
        "sensor.hph_cop_monthly",
        "sensor.hph_scop",
        "sensor.hph_thermal_power",
        "sensor.hph_thermal_daily",
        "sensor.hph_thermal_monthly",
        "sensor.hph_thermal_yearly",
        "sensor.hph_electrical_daily",
        "sensor.hph_electrical_monthly",
        "sensor.hph_electrical_yearly",
        "sensor.hph_operating_mode",
        "sensor.hph_cycles_today",
        "sensor.hph_short_cycles_today",
        "sensor.hph_advisor_summary",
    ]

    rows = [["timestamp", "entity_id", "state", "unit"]]
    ts = now.isoformat()
    for eid in sensor_ids:
        st = hass.states.get(eid)
        if st:
            unit = st.attributes.get("unit_of_measurement", "")
            rows.append([ts, eid, st.state, unit])

    try:
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerows(rows)
        await hass.async_add_executor_job(
            Path(target_path).write_text, out.getvalue(), "utf-8"
        )
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
                "message": f"Export written to {target_path} ({fmt}).",
            },
            blocking=True,
        )
        _LOGGER.info("HPH export written to %s", target_path)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("HPH export failed: %s", exc)


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

    # Seed the external entity text helpers.
    _text_map = {
        "text.hph_src_ext_thermal_power": external_thermal_power,
        "text.hph_src_ext_thermal_energy": external_thermal_energy,
        "text.hph_src_ext_electrical_power": external_electrical_power,
        "text.hph_src_ext_electrical_energy": external_electrical_energy,
        "text.hph_indoor_temp_entity": data.get("indoor_temp_entity", ""),
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
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_HASS_CONFIG: hass.config.path(),
        "options": dict(entry.options) if entry.options else {},
        "data": dict(entry.data) if entry.data else {},
    }

    # Deploy dashboard + efficiency package; migrate old automation packages.
    deployed = await async_deploy_yaml_packages(hass)
    hass.data[DOMAIN][entry.entry_id]["bootstrap"] = deployed

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
    preset = entry.data.get("vendor_preset")
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
    model = entry.data.get("pump_model")
    if model:
        await async_apply_pump_model(hass, model)

    # Apply step-3 external sensor config from config flow.
    await _apply_sensor_config(hass, entry.data)

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
    )

    all_unsubs: list = []
    for coord in [cycles, advisor, diagnostics, control, control_ext, programs, bridge, export, efficiency, models]:
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
