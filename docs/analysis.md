# Analysis module — KI / smart observation

🌐 English

Heat Pump Hero ships an analysis layer that observes operation over
time and produces **concrete, actionable recommendations** (in K, not
hand-wavy hints). Three layers — only L1 is enabled by default; L2 is
opt-in; L3 is roadmap.

## Layer 1 — Statistical observation (always on)

Implemented in `packages/hph_analysis.yaml`. Pure HA template + statistics
platform. No external dependency.

**What it observes**

- Indoor temperature deviation vs target over a rolling N-day window
  (default: 7 days)
- Smoothing via the HA `statistics` platform (`average_linear` over
  ≤168 hours)

**What it recommends**

- Heating-curve adjustment in K, written to
  `sensor.hph_advisor_analysis.attributes.recommendation_k`
- Direction: positive = raise the curve, negative = lower
- Suppressed inside the configurable dead band (default ±0.5 K)

**Configuration**

Set in dashboard *Configuration → Analysis*:

| Helper | Purpose |
|---|---|
| `input_text.hph_indoor_temp_entity` | reference room sensor entity-ID (required) |
| `input_text.hph_indoor_target_entity` | target sensor (optional; falls back to default) |
| `input_number.hph_indoor_target_default` | fallback target in °C (default 21) |
| `input_number.hph_analysis_window_days` | rolling window length (3-30 days) |
| `input_number.hph_analysis_dead_band_k` | recommendations suppressed ≤ this delta |

The advisor surfaces in the Optimization view with a coloured tile;
the deviation feeds the aggregate traffic-light.

## Layer 2 — Linear regression (opt-in script)

`scripts/analyze_heating_curve.py` fits `supply_temp = a + b · outdoor_temp`
on the last N days of compressor-on samples and writes a one-line
recommendation to `input_text.hph_heating_curve_recommendation`.
The advisor displays it alongside the L1 message.

**Run manually**

```bash
HA_BASE_URL=http://homeassistant.local:8123 \
HA_TOKEN=<long-lived-token> \
python3 /config/scripts/analyze_heating_curve.py --days 14
```

**Schedule nightly** in `configuration.yaml`:

```yaml
shell_command:
  hph_analyze_curve: >-
    HA_BASE_URL=http://localhost:8123
    HA_TOKEN=!secret hph_export_token
    python3 /config/scripts/analyze_heating_curve.py --days 14

automation:
  - alias: HPH — analyze heating curve nightly
    trigger:
      - platform: time
        at: "03:30:00"
    action:
      - service: shell_command.hph_analyze_curve
```

**Output format** (one line, ≤ 255 chars):
```
moderate — typical for mixed underfloor / radiators. slope -0.65 K/K, intercept 35.4 °C, R²=0.78, n=412.
```

## Layer 3 — LLM-based (roadmap, v0.7+)

A future custom integration could expose Heat Pump Hero's structured
data to an LLM via HA's `conversation` integration, enabling questions
like *"Why did the unit cycle so much last Wednesday?"*. Not implemented
in v0.6 — would require either an OpenAI/Anthropic API key or a local
model (e.g. via Ollama) plus careful tool-use design.

For now: L1 + L2 cover the actual practical recommendations users need.

## Why this isn't "real AI"

Industry rule of thumb: if a problem has a simple statistical formulation
that explains a clear physical relationship (heating curve = linear in
outdoor temp), regression beats neural networks every time. Heat-pump
tuning is in that category — no need for opacity. The L1 + L2 approach
is also fully introspectable: every recommendation traces back to
specific input numbers and helpers the user can override.

## Worked example

Reference room sensor reports 22.3 °C average over 7 days. Target is
21.0 °C. Smoothed deviation = +1.3 K (above dead band of 0.5 K).

Advisor message: *"Indoor temperature averaged 1.3 K above target over
the last 7 days. Recommend lowering the heating curve by ~1.3 K, or
raising the target by the same amount if the room is comfortable."*

`recommendation_k` attribute = `-1.3`. User decides whether to act.
