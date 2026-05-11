"""Apply vendor preset / pump model — seeds helper entities.

Triggered:
  - Once on async_setup_entry from config-flow data
  - On state-change of input_select.hph_vendor_preset (legacy YAML
    automation in v0.8 — kept until phase 3 finishes)
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from ..const import MODEL_CAPABILITIES, PUMP_MODELS, VENDOR_PRESETS

_LOGGER = logging.getLogger(__name__)


async def async_apply_vendor_preset(
    hass: HomeAssistant, preset: str, model: str = ""
) -> None:
    """Set every source / write helper to the entity-IDs for *preset*.

    When *model* is provided and has an entry in MODEL_CAPABILITIES, every
    ``hph_src_*`` helper whose suffix is NOT in the capability set is written
    as ``""`` (empty) — preventing phantom entity references for sensors the
    physical hardware does not expose (e.g. Fan 2 on a single-fan J/L-series).

    ``hph_ctrl_write_*`` helpers are never capability-gated because control
    surfaces are vendor-gated (empty default in VENDOR_PRESETS) rather than
    model-gated.
    """
    payload = VENDOR_PRESETS.get(preset)
    if payload is None:
        _LOGGER.warning("Unknown vendor preset %s — skipping auto-fill", preset)
        return

    caps = MODEL_CAPABILITIES.get(model) if model else None
    gated: list[str] = []

    for unique_id, value in payload.items():
        entity_id = f"text.{unique_id}"
        if caps is not None and unique_id.startswith("hph_src_"):
            suffix = unique_id.removeprefix("hph_src_")
            if suffix not in caps:
                value = ""  # sensor not present on this model
                gated.append(unique_id)
        await hass.services.async_call(
            "text",
            "set_value",
            {"entity_id": entity_id, "value": value},
            blocking=False,
        )

    if gated:
        _LOGGER.info(
            "Applied vendor preset %s (model=%s) — %d helpers seeded, "
            "%d capability-gated (set empty): %s",
            preset, model, len(payload), len(gated), ", ".join(gated),
        )
    else:
        _LOGGER.info(
            "Applied vendor preset %s (model=%s) — %d helpers seeded",
            preset, model or "unspecified", len(payload),
        )


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
    # Also reflect the chosen model in the select entity so the UI shows it.
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.hph_pump_model", "option": model},
        blocking=False,
    )
    _LOGGER.info("Applied model %s — 4 thresholds set, select entity updated", model)
