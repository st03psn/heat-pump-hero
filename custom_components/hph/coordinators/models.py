"""HeatPump Hero — models coordinator.

Ports hph_models.yaml automations:
  - hph_model_apply_thresholds  (select.hph_pump_model state change)
  - hph_vendor_preset_apply     (select.hph_vendor_preset state change)

The vendor-preset logic is already in helpers/vendor_apply.py and is also
called from __init__.py on first setup. This coordinator re-applies when
the user changes the preset at runtime via the select entity.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

_MODEL_THRESHOLDS: dict[str, dict[str, float]] = {
    "panasonic_j_aqj": {"min_hz": 22, "max_hz": 90,  "min_flow": 11, "max_supply": 55},
    "panasonic_k_aqk": {"min_hz": 18, "max_hz": 90,  "min_flow": 11, "max_supply": 55},
    "panasonic_l_aql": {"min_hz": 16, "max_hz": 110, "min_flow": 9,  "max_supply": 55},
    "panasonic_tcap":  {"min_hz": 16, "max_hz": 140, "min_flow": 9,  "max_supply": 55},
    "panasonic_m_aqm": {"min_hz": 16, "max_hz": 120, "min_flow": 8,  "max_supply": 75},
    "vaillant_arotherm": {"min_hz": 16, "max_hz": 110, "min_flow": 9, "max_supply": 75},
}
_DEFAULT_THRESHOLDS = {"min_hz": 16, "max_hz": 110, "min_flow": 9, "max_supply": 55}


async def async_setup(hass: HomeAssistant, entry: ConfigEntry) -> list[Callable]:
    """Register model listeners. Returns unsubscribe list."""
    unsubs: list[Callable] = []

    # ── Model thresholds ─────────────────────────────────────────────────────
    @callback
    def _on_model_change(event: Event) -> None:
        new = event.data.get("new_state")
        if new is None or new.state in ("unknown", "unavailable"):
            return
        hass.async_create_task(_apply_model(new.state))

    async def _apply_model(model: str) -> None:
        t = _MODEL_THRESHOLDS.get(model, _DEFAULT_THRESHOLDS)
        await hass.services.async_call(
            "number", "set_value",
            {"entity_id": "number.hph_model_compressor_min_hz", "value": t["min_hz"]},
            blocking=True,
        )
        await hass.services.async_call(
            "number", "set_value",
            {"entity_id": "number.hph_model_compressor_max_hz", "value": t["max_hz"]},
            blocking=True,
        )
        await hass.services.async_call(
            "number", "set_value",
            {"entity_id": "number.hph_model_min_flow_lpm", "value": t["min_flow"]},
            blocking=True,
        )
        await hass.services.async_call(
            "number", "set_value",
            {"entity_id": "number.hph_model_max_supply_c", "value": t["max_supply"]},
            blocking=True,
        )
        await hass.services.async_call(
            "persistent_notification", "create",
            {
                "notification_id": "hph_model_change",
                "title": "HeatPump Hero — model thresholds updated",
                "message": (
                    f"Model set to {model}. Compressor min/max Hz, min flow L/min and "
                    "max supply °C were auto-set to typical values for this model. "
                    "Review under Configuration → Model thresholds."
                ),
            },
            blocking=True,
        )

    unsubs.append(
        async_track_state_change_event(
            hass, ["select.hph_pump_model"], _on_model_change
        )
    )

    # ── Vendor preset ────────────────────────────────────────────────────────
    @callback
    def _on_preset_change(event: Event) -> None:
        new = event.data.get("new_state")
        if new is None or new.state in ("unknown", "unavailable", "keep_current"):
            return
        hass.async_create_task(_apply_preset(new.state))

    async def _apply_preset(preset: str) -> None:
        from ..helpers.vendor_apply import async_apply_vendor_preset
        await async_apply_vendor_preset(hass, preset)
        # Reset selector back to keep_current
        await hass.services.async_call(
            "select", "select_option",
            {"entity_id": "select.hph_vendor_preset", "option": "keep_current"},
            blocking=True,
        )

    unsubs.append(
        async_track_state_change_event(
            hass, ["select.hph_vendor_preset"], _on_preset_change
        )
    )

    _LOGGER.debug("HPH models coordinator started")
    return unsubs
