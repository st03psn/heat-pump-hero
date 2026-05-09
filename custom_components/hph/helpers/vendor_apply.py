"""Apply vendor preset / pump model — seeds helper entities.

Triggered:
  - Once on async_setup_entry from config-flow data
  - On state-change of input_select.hph_vendor_preset (legacy YAML
    automation in v0.8 — kept until phase 3 finishes)
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from ..const import PUMP_MODELS, VENDOR_PRESETS

_LOGGER = logging.getLogger(__name__)


async def async_apply_vendor_preset(hass: HomeAssistant, preset: str) -> None:
    """Set every source / write helper to the entity-IDs for `preset`."""
    payload = VENDOR_PRESETS.get(preset)
    if payload is None:
        _LOGGER.warning("Unknown vendor preset %s — skipping auto-fill", preset)
        return

    for unique_id, value in payload.items():
        # Helpers expose a service `set_value` via Text/Select platforms.
        entity_id = f"text.{unique_id}"
        await hass.services.async_call(
            "text",
            "set_value",
            {"entity_id": entity_id, "value": value},
            blocking=False,
        )
    _LOGGER.info("Applied vendor preset %s — %d helpers seeded", preset, len(payload))


async def async_apply_pump_model(hass: HomeAssistant, model: str) -> None:
    """Set the four model-threshold numbers for the chosen model."""
    spec = PUMP_MODELS.get(model)
    if spec is None:
        _LOGGER.warning("Unknown pump model %s — skipping threshold apply", model)
        return

    mapping = {
        "hph_model_compressor_min_hz": spec.get("min_hz"),
        "hph_model_compressor_max_hz": spec.get("max_hz"),
        "hph_model_min_flow_lpm": spec.get("min_flow"),
        "hph_model_max_supply_c": spec.get("max_supply"),
    }
    for unique_id, value in mapping.items():
        if value is None:
            continue
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": f"number.{unique_id}", "value": value},
            blocking=False,
        )
    _LOGGER.info("Applied model %s — 4 thresholds set", model)
