"""HeatPump Hero — models coordinator.

Ports hph_models.yaml automations:
  - hph_model_apply_thresholds  (select.hph_pump_model state change)
  - hph_vendor_preset_apply     (select.hph_vendor_preset state change)

The vendor-preset logic is already in helpers/vendor_apply.py and is also
called from __init__.py on first setup. This coordinator re-applies when
the user changes the preset at runtime via the select entity.

Teaser vendors (non-Panasonic): selecting them resets to keep_current and
shows a "coming soon" notification. No helpers are changed. The options are
visible in the dropdown as a preview of planned multi-vendor support.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

# Vendors with full HPH support (source + control helpers, capability gating).
_SUPPORTED_VENDORS = frozenset({"panasonic_heishamon", "panasonic_heishamon_aquarea"})

# Vendors visible in the dropdown as previews, but not yet fully implemented.
# Selecting one resets immediately and shows a notification — no helpers change.
_TEASER_VENDOR_LABELS: dict[str, str] = {
    "daikin_altherma_core":        "Daikin Altherma",
    "mitsubishi_melcloud_core":    "Mitsubishi MELCloud",
    "vaillant_arotherm_mypyllant": "Vaillant aroTHERM",
    "stiebel_eltron_isg":          "Stiebel Eltron ISG",
    "generic_modbus":              "Generic (Modbus)",
    "generic_mqtt":                "Generic (MQTT)",
}

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
        # Teaser vendors: reset immediately, no helpers changed.
        if preset in _TEASER_VENDOR_LABELS:
            label = _TEASER_VENDOR_LABELS[preset]
            await hass.services.async_call(
                "select", "select_option",
                {"entity_id": "select.hph_vendor_preset", "option": "keep_current"},
                blocking=True,
            )
            await hass.services.async_call(
                "persistent_notification", "create",
                {
                    "notification_id": "hph_vendor_teaser",
                    "title": f"HeatPump Hero — {label} support coming soon",
                    "message": (
                        f"{label} is on the roadmap but not yet fully supported. "
                        "Your current configuration was not changed. "
                        "Follow the HeatPump Hero changelog for updates."
                    ),
                },
                blocking=False,
            )
            _LOGGER.info("HPH vendor teaser: %s selected, reset to keep_current", preset)
            return

        # Supported vendor: read current model for capability gating, then apply.
        model_st = hass.states.get("select.hph_pump_model")
        model = model_st.state if model_st and model_st.state not in ("unknown", "unavailable") else ""
        from ..helpers.vendor_apply import async_apply_vendor_preset
        await async_apply_vendor_preset(hass, preset, model=model)
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
