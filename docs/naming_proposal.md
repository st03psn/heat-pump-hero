# Naming proposal

🌐 English

The current name **Heat Pump Hero** is heavily Heishamon-branded. With the
v0.4 source-adapter, vendor presets covering Daikin / Vaillant /
Mitsubishi / Stiebel / generic, and Panasonic M-series support, the
Heishamon-only association no longer matches the scope.

## Criteria

1. **Universal** — not vendor-specific
2. **Modern** — connects to the energy transition (Wärmewende)
3. **Heat-pump-clear** — instantly recognisable as heat-pump tooling
4. **Concise** — single word preferred, ≤ 9 chars
5. **EN / DE / NL** — works as a brand in all three languages
6. **Pronounceable** — no awkward acronyms

## Top candidates

### **HeatLens** ⭐ recommended

- Universal, no vendor lock-in
- "Lens" = analytical viewpoint, fits the dashboard / advisor purpose
- Modern, professional, easy to remember
- Pronounceable in EN / DE / NL identically
- Domain `heatlens.io` likely available

### **HeatHub**

- Direct, simple, conveys "central place for heat data"
- Slightly generic, but exactly matches what the project is
- Easy on social / GitHub
- Risk: heatpump-related projects called HeatHub already exist

### **Hearth**

- Old English for fireplace — evokes home heating
- Single-word, memorable
- Works in DE/NL phonetically
- Risk: "hearth" implies traditional/wood heating; less obvious for
  modern heat pumps

### **AquaPulse**

- A2W ("aqua") + dynamic ("pulse")
- Distinct, brandable
- Risk: not obviously about heat pumps; "Aqua" also suggests aquariums

### **Caldera**

- Spanish/Italian for boiler/cauldron; also a volcanic term (lots of heat)
- Strong sense of warmth & energy
- Risk: existing brands use Caldera in cooling / boiler space

## Rationale for HeatLens

It captures the actual project value: Heat Pump Hero doesn't replace the
heat pump's controls, it provides a **lens** through which to see it
clearly — efficiency, faults, optimisation. The name de-couples from
Heishamon without losing any meaning, and it works equally well for
Heishamon, Daikin, Vaillant, Mitsubishi, Stiebel users.

## Migration plan (when accepted)

1. Decide name in an issue / discussion.
2. Rename GitHub repository — GitHub keeps redirects from `st03psn/Heat Pump Hero`.
3. Rename `manifest.json` / `hacs.json` / `info.md`.
4. **Keep entity-IDs** stable (`hph_*`) for v1.x — too disruptive
   to rename. Document as "legacy prefix from project's first name".
5. Domain registration if we go that direction.
6. Logo / icon update — coordinate with the screenshots placeholders.

## What stays

- All entity-IDs, helper names, package filenames keep `hph_`
  prefix in v1 to avoid breaking installs.
- Tag deprecation path for v2 if a clean rename is later desired.
- Repo description / README headline switches to the new name; the
  first paragraph mentions the historical name once for discoverability.

## Decision

This is a community decision. Track in
[issue #X](https://github.com/st03psn/heat-pump-hero/issues) once filed.
