"""HeatPump Hero — efficiency coordinator.

Ports hph_efficiency.yaml automation:
  - hph_tariff_switch  (sensor.hph_operating_mode state change)

The utility_meter entities (hph_thermal_daily_split etc.) are defined in
hph_efficiency.yaml which is still deployed as a platform config package.
The tariff-switch service call targets those entities.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

_SPLIT_METERS = [
    "sensor.hph_thermal_daily_split",
    "sensor.hph_thermal_monthly_split",
    "sensor.hph_thermal_yearly_split",
    "sensor.hph_electrical_daily_split",
    "sensor.hph_electrical_monthly_split",
    "sensor.hph_electrical_yearly_split",
]


async def async_setup(hass: HomeAssistant, entry: ConfigEntry) -> list[Callable]:
    """Register efficiency listeners. Returns unsubscribe list."""
    unsubs: list[Callable] = []

    @callback
    def _on_mode_change(event: Event) -> None:
        new = event.data.get("new_state")
        if new is None:
            return
        mode = new.state
        if mode == "dhw":
            tariff = "dhw"
        elif mode == "cooling":
            tariff = "cooling"
        else:
            tariff = "heating"
        hass.async_create_task(_switch_tariff(tariff))

    async def _switch_tariff(tariff: str) -> None:
        try:
            await hass.services.async_call(
                "utility_meter", "select_tariff",
                {"entity_id": _SPLIT_METERS, "tariff": tariff},
                blocking=True,
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Tariff switch skipped (utility_meter may not be loaded): %s", exc)

    unsubs.append(
        async_track_state_change_event(
            hass, ["sensor.hph_operating_mode"], _on_mode_change
        )
    )

    # Auto-recompute when a source helper changes — without this, the
    # _active sensors only re-evaluate on the next state change of the
    # newly-pointed-at entity, which may be hours away if the heat pump
    # is off. Debounced lightly so a burst of helper edits during setup
    # doesn't fire 17 service calls.
    _RECOMPUTE_TARGETS = [
        "text.hph_src_outlet_temp",
        "text.hph_src_inlet_temp",
        "text.hph_src_flow_rate",
        "text.hph_src_internal_power",
        "text.hph_src_internal_thermal_power",
        "text.hph_src_external_thermal_power",
        "text.hph_src_external_thermal_energy",
        "text.hph_src_external_electrical_power",
        "text.hph_src_external_electrical_energy",
        "select.hph_thermal_source",
        "select.hph_electrical_source",
    ]

    @callback
    def _on_source_helper_change(_event: Event) -> None:
        async def _fire() -> None:
            try:
                await hass.services.async_call(
                    "hph", "recompute", {}, blocking=False,
                )
            except Exception as exc:  # noqa: BLE001
                _LOGGER.debug("hph.recompute auto-fire failed: %s", exc)
        hass.async_create_task(_fire())

    unsubs.append(
        async_track_state_change_event(
            hass, _RECOMPUTE_TARGETS, _on_source_helper_change
        )
    )

    _LOGGER.debug("HPH efficiency coordinator started")
    return unsubs
