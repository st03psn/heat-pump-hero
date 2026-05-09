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

from .bootstrap import (
    async_clean_deployed_files,
    async_deploy_yaml_packages,
    async_register_dashboard,
)
from .const import (
    DASHBOARD_URL_PATH,
    DATA_HASS_CONFIG,
    DOMAIN,
    PLATFORMS,
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

    # Apply chosen vendor preset (one-shot on first install).
    preset = entry.data.get("vendor_preset")
    if preset and preset != "keep_current":
        from .helpers.vendor_apply import async_apply_vendor_preset
        await async_apply_vendor_preset(hass, preset)

    # Apply chosen pump model thresholds.
    model = entry.data.get("pump_model")
    if model:
        from .helpers.vendor_apply import async_apply_pump_model
        await async_apply_pump_model(hass, model)

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
