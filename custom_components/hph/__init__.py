"""HeatPump Hero — Home Assistant custom integration.

Phase 1: thin Python integration that
  - registers helper platforms (text/number/select/switch/datetime/button)
    with the same unique_ids as the v0.8 YAML helpers
  - bootstraps the YAML packages that haven't been ported yet (sensors
    + automations) from the bundled `data/` directory into
    `<config>/packages/`
  - auto-registers the dashboard YAML so users don't need
    "Settings → Dashboards → Add from YAML" anymore
  - on UI-uninstall, cleans up every file the integration ever wrote

Phases 2 (sensors) and 3 (automations) shrink the bootstrap footprint
to zero.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import discovery

from .bootstrap import (
    async_clean_deployed_files,
    async_deploy_yaml_packages,
    async_register_dashboard,
)
from .const import (
    DASHBOARD_URL_PATH,
    DATA_BOOTSTRAP_DONE,
    DATA_HASS_CONFIG,
    DOMAIN,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration's domain key. ConfigEntry-only — no YAML config."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HeatPump Hero from a config entry."""
    _LOGGER.info("Setting up HeatPump Hero entry %s", entry.entry_id)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_HASS_CONFIG: hass.config.path(),
        "options": dict(entry.options) if entry.options else {},
        "data": dict(entry.data) if entry.data else {},
    }

    # Phase 1: deploy YAML packages (sensors + automations not yet ported).
    deployed = await async_deploy_yaml_packages(hass)
    hass.data[DOMAIN][entry.entry_id][DATA_BOOTSTRAP_DONE] = deployed

    # Forward to platforms (text/number/select/switch/datetime/button).
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Auto-register the dashboard (idempotent).
    try:
        await async_register_dashboard(hass)
    except Exception as exc:  # noqa: BLE001 — dashboard register is best-effort
        _LOGGER.warning("Dashboard auto-registration failed: %s", exc)

    # Apply the chosen vendor preset to seed source helpers (one-shot).
    preset = entry.data.get("vendor_preset")
    if preset and preset != "keep_current":
        from .helpers.vendor_apply import async_apply_vendor_preset

        await async_apply_vendor_preset(hass, preset)

    # Apply the chosen pump model thresholds.
    model = entry.data.get("pump_model")
    if model:
        from .helpers.vendor_apply import async_apply_pump_model

        await async_apply_pump_model(hass, model)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options-flow updates by reloading the config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry — entities are unloaded but bootstrapped YAML stays.

    Full file cleanup happens only on `async_remove_entry` (= user clicks
    Delete in the UI). This separation lets HA reload the integration
    without nuking deployed YAML.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Aggressive cleanup on UI-uninstall: remove every file we wrote.

    Recorder DB / Long-Term Statistics are NOT touched (HA core handles
    that on entity-registry removal naturally). User exports under
    `<config>/www/heishahub_exports/` are user data — left alone.
    """
    _LOGGER.info("Removing HeatPump Hero — aggressive file cleanup begins")
    await async_clean_deployed_files(hass)
    _LOGGER.info("HeatPump Hero removed cleanly")
