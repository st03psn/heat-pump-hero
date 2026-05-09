# CLAUDE.md

Projektkontext und Regeln für Claude Code. **Kurz halten** — alles, was hier steht, frisst Context-Tokens und konkurriert mit dem eigentlichen Code.

---

## Projekt

- **Was:** Home Assistant Setup — <!-- TODO: Eigenes HA-Setup / Custom Component "xy" / Beides --> 
- **HA-Version:** <!-- TODO: z.B. 2026.5.x, OS / Container / Core / Supervised -->
- **Python:** 3.13 (HA Core ≥ 2025.12 erfordert 3.13)
- **DB-Backend:** <!-- TODO: SQLite (default) / MariaDB / PostgreSQL -->
- **Editor-Pfad zur Config:** `/config` (im Container) bzw. `<repo-root>/config` lokal

## Repo-Layout

```
config/
  configuration.yaml        # Hauptdatei, möglichst schlank
  secrets.yaml              # NIE committen, ist in .gitignore
  automations.yaml          # UI-verwaltet, NICHT manuell editieren
  packages/                 # Modulare YAML-Pakete (bevorzugter Ort für eigene Logik)
  custom_components/<name>/ # Eigene Integration(en)
    __init__.py
    manifest.json
    config_flow.py
    const.py
    coordinator.py
    sensor.py / switch.py / ...
    strings.json
    translations/
tests/
  custom_components/<name>/ # pytest-homeassistant-custom-component
```

---

## Workflow-Regeln (für Claude)

1. **Erst planen, dann coden.** Bei allem über trivial: Plan vorlegen, ich approve, dann implementieren.
2. **Nichts behaupten ohne Validierung.** Nach jeder Änderung die passenden Befehle aus dem Abschnitt "Commands" laufen lassen und Output zeigen.
3. **Keine spekulativen Refactorings** außerhalb des Aufgabenscopes. Wenn dir was auffällt → nennen, nicht anfassen.
4. **Bei zweimal fehlgeschlagenem Fix stoppen**, Lage zusammenfassen, nach Richtungsentscheidung fragen.
5. **Nicht anfassen:** `secrets.yaml`, `.storage/`, `automations.yaml` (UI), `home-assistant_v2.db`.

---

## YAML-Konventionen

- **2 Spaces**, keine Tabs. Listen mit `-` auf neuer Zeile mit Einrückung.
- **`!include` und `!include_dir_merge_named`** zur Modularisierung statt monolithischer `configuration.yaml`.
- **Eigene Logik gehört in `packages/`** (per `homeassistant: packages: !include_dir_named packages`), nicht in die Hauptdatei.
- **Secrets via `!secret key`** — niemals Tokens, IPs, Passwörter inline.
- **Entity-IDs in `snake_case`**, Domains-Präfix sinnvoll: `sensor.kueche_temperatur`, nicht `sensor.sensor1`.
- **Templates:** Jinja2 in `{{ }}`, defensiv schreiben — `states('sensor.x') | float(0)`, nie `| float` ohne Default. `is_state()` und `state_attr()` statt String-Vergleichen auf `states.x.y.state`.
- **Keine YAML-Anker-Magie** zur Wiederverwendung — `script:` oder `template:` sind lesbarer.
- **Trigger-IDs nutzen** in Multi-Trigger-Automationen statt `{{ trigger.platform }}`-Switching.

## Python-Konventionen (Custom Components)

- **Async-first.** Alles I/O ist `async def`. Niemals `requests`/`time.sleep`/blocking File-IO im Event-Loop. Wenn unvermeidbar: `await hass.async_add_executor_job(fn, *args)`.
- **Type Hints überall**, `from __future__ import annotations` oben in jedem Modul. `mypy --strict`-tauglich.
- **Konstanten** in `const.py`, kein Magic-String im Code.
- **Config Flow ist Pflicht** für neue Integrationen — kein YAML-Setup mehr für User-facing Configs.
- **DataUpdateCoordinator** für alles, was pollt. Keine eigenen Polling-Loops in Entities.
- **Entity-Klassen erben von der Domain-Base** (`SensorEntity`, `BinarySensorEntity`, ...) und setzen `_attr_*` statt Properties zu überschreiben, wo möglich.
- **`unique_id` immer setzen**, sonst keine UI-Verwaltung möglich.
- **`DeviceInfo`** zurückgeben für sauberes Device-Grouping.
- **Logging:** `_LOGGER = logging.getLogger(__name__)`, keine `print()`. `_LOGGER.debug/info/warning/error` — keine f-Strings im Logger-Call (`_LOGGER.debug("x=%s", x)`).
- **Exceptions:** `HomeAssistantError`, `ConfigEntryNotReady`, `ConfigEntryAuthFailed` — keine generischen `Exception`-Raises an die Core-API.
- **`manifest.json`:** `"iot_class"` korrekt setzen, `"requirements"` mit gepinnten Versionen, `"version"` bei jeder Änderung hochziehen (für HACS).

## SQL / Recorder

- **Lesender Zugriff bevorzugt über `recorder.history` / `recorder.statistics`-APIs**, nicht direkt auf die DB.
- **Direkte Queries nur read-only** und über `recorder.get_instance(hass).async_add_executor_job(...)` — die Recorder-DB hat ihren eigenen Thread.
- **Niemals in `states`/`events`-Tabellen schreiben.**
- **Long-term Statistics** (Tabelle `statistics`/`statistics_short_term`) nur über die offizielle Statistics-API anfassen.
- **`sql`-Integration** für Custom-Sensoren bevorzugen vor eigenem Python, wenn es nur ein SELECT ist.
- **Indizes beachten:** Queries auf `states_meta.entity_id` + `states.last_updated_ts` sind schnell, alles andere wird auf großen DBs schmerzhaft.

---

## Commands

```bash
# YAML-Validierung (im HA-Container oder via CLI)
hass --script check_config -c ./config

# Custom-Component-Validierung
python -m script.hassfest                  # bei Core-Contribs
hassfest --action validate                 # bei Custom Components

# Lint & Format (Home-Assistant-Standard ist ruff)
ruff check .
ruff format .

# Typing
mypy custom_components/<name>

# Tests (pytest-homeassistant-custom-component)
pytest tests/ -x --cov=custom_components.<name> --cov-report=term-missing

# Einzeltests schnell
pytest tests/custom_components/<name>/test_sensor.py::test_state -x -vv
```

**Definition of Done für jede Änderung:** `ruff check`, `ruff format --check`, `mypy`, `pytest` — alles grün. Bei YAML-Änderungen zusätzlich `check_config`.

---

## Häufige Fallen (bitte vermeiden)

- **Blocking Calls im Event-Loop** (`requests.get`, `open()` ohne `aiofiles`, `time.sleep`) → HA loggt `Detected blocking call` und friert kurzzeitig ein.
- **`hass.data[DOMAIN]` ohne Setup-Guard** → KeyErrors bei Reload. Lieber `hass.data.setdefault(DOMAIN, {})`.
- **State-Updates in `__init__`** der Entity → kommt vor Registry-Anmeldung an, geht verloren. Erst in `async_added_to_hass`.
- **Templates, die auf `unknown`/`unavailable` nicht prüfen** → Sensoren springen auf `None`, Automationen feuern falsch. Immer `if states('x') not in ('unknown','unavailable','none')` voranstellen oder `availability_template` setzen.
- **Recorder-DB direkt mit eigenem Connection-Pool** → Lock-Konflikte. Immer über die Recorder-Instance.
- **`async_track_state_change`** ist deprecated → `async_track_state_change_event` verwenden.
- **`entity_id` aus YAML hart kodieren** in Custom Components → User kann sie umbenennen. `unique_id`-basiert auflösen.

---

## Stilrichtlinien für Antworten

- Bei Code-Änderungen: vorher kurz nennen, was und warum. Danach Diff oder Datei.
- Keine Beispiel-Tokens / Beispiel-IPs in committeten Code, immer `!secret`.
- Bei Vorschlägen, die HA-Core-Patterns brechen, explizit darauf hinweisen.
- Wenn unklar, was der User will: **fragen**, nicht raten — eine konkrete Frage, nicht drei.

<!-- TODO: Eigene Integrationen, externe APIs, MQTT-Topics, Zigbee-Koordinator, etc. hier ergänzen -->
