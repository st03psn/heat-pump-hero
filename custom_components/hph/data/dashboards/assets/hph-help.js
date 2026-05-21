/* HeatPump Hero — inline help popup custom element.
 *
 * Usage in Lovelace YAML:
 *
 *   # Inline content (no i18n):
 *   - type: custom:hph-help
 *     title: My help title
 *     content: |
 *       Markdown body here.
 *
 *   # Translation key (i18n via help_<lang>.json, follows hass.config.language):
 *   - type: custom:hph-help
 *     translation_key: efficiency_quality
 *
 *   # Heading-only (no "?" button) — for section titles without help content:
 *   - type: custom:hph-help
 *     translation_key: section_my_section
 *     button: false
 *
 * Renders as a heading + small "?" icon button. Click opens a modal with the
 * title and markdown content. Closes on backdrop click, Esc, or close button.
 *
 * Translation files are served from /hph_assets/help_<lang>.json (mounted by
 * HPH's __init__.py). Fetched lazily on first paint, cached process-wide.
 * Falls back to inline title/content if translation_key is missing or fetch
 * fails. No HACS dependency.
 *
 * IMPORTANT: this file is loaded via add_extra_js_url as a classic <script>,
 * not an ES module. To survive being loaded twice (e.g. across HA reloads
 * within the same browser session) we wrap everything in an IIFE so toplevel
 * `const` declarations don't collide and abort the entire script.
 */

(function () {
"use strict";

// NOTE: do NOT early-return when hph-help is already registered — this file
// also defines <hph-tile>, and an early return after a stale load of an older
// version (which only had hph-help) would leave hph-tile undefined and every
// hph-tile card would show "Configuration error". Each customElements.define
// below is guarded individually instead, so re-running is always safe.

// Module-level i18n cache: { lang: { key: {title, content} } }
const __HPH_HELP_STRINGS__ = {};
const __HPH_HELP_PENDING__ = {};

async function __hphLoadHelpStrings(lang) {
  if (__HPH_HELP_STRINGS__[lang]) return __HPH_HELP_STRINGS__[lang];
  if (__HPH_HELP_PENDING__[lang]) return __HPH_HELP_PENDING__[lang];
  __HPH_HELP_PENDING__[lang] = (async () => {
    try {
      const res = await fetch(`/hph_assets/help_${lang}.json`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      __HPH_HELP_STRINGS__[lang] = data;
      return data;
    } catch (err) {
      console.warn(`[hph-help] failed to load help_${lang}.json:`, err);
      __HPH_HELP_STRINGS__[lang] = {};
      return {};
    }
  })();
  return __HPH_HELP_PENDING__[lang];
}

function __hphCurrentLang() {
  // Honour HA's selected language (Settings → System → General). Defaults
  // to en if not yet set on initial paint. Falls back from regional variants
  // (e.g. de-DE → de) and only en is guaranteed to exist.
  try {
    const hass =
      document.querySelector("home-assistant")?.hass ||
      document.querySelector("hass-main")?.hass;
    const raw = hass?.language || hass?.locale?.language || "en";
    const lang = String(raw).toLowerCase().split("-")[0];
    return ["en", "de", "nl"].includes(lang) ? lang : "en";
  } catch (_e) {
    return "en";
  }
}

class HphHelpCard extends HTMLElement {
  setConfig(config) {
    if (!config) throw new Error("hph-help: config required");
    this._config = {
      title: config.title || "",
      subtitle: config.subtitle || "",
      content: config.content || "",
      icon: config.icon || "mdi:help-circle-outline",
      label: config.label || "",
      // Translation key — when set, title+content come from help_<lang>.json.
      translation_key: config.translation_key || null,
      // When true (default), the card renders the title as an inline H3
      // next to the help button. Set heading: false to render the button
      // alone (e.g. when the title is already provided by a sibling card).
      heading: config.heading !== false,
      // When false, the "?" button is suppressed — useful for heading-only
      // section titles that have no help content to show.
      button: config.button !== false,
    };
    // Render immediately with placeholder; resolve translations async.
    // Lovelace's setConfig contract is synchronous — we must not await here.
    this._rendered = false;
    this._render();
    if (this._config.translation_key) {
      this._resolveStrings()
        .then(() => this._updateTexts())
        .catch((err) => console.warn("[hph-help] resolve failed:", err));
    }
  }

  async _resolveStrings() {
    if (!this._config.translation_key) return;
    const lang = __hphCurrentLang();
    const strings = await __hphLoadHelpStrings(lang);
    const entry = strings[this._config.translation_key];
    if (entry) {
      if (!this._config.title) this._config.title = entry.title || "";
      if (!this._config.subtitle) this._config.subtitle = entry.subtitle || "";
      if (!this._config.content) this._config.content = entry.content || "";
    } else if (lang !== "en") {
      const en = await __hphLoadHelpStrings("en");
      const enEntry = en[this._config.translation_key];
      if (enEntry) {
        if (!this._config.title) this._config.title = enEntry.title || "";
        if (!this._config.subtitle) this._config.subtitle = enEntry.subtitle || "";
        if (!this._config.content) this._config.content = enEntry.content || "";
      }
    }
    if (!this._config.title) this._config.title = "Help";
  }

  _updateTexts() {
    // Update inline heading text in-place after async translation resolution.
    const heading = this.querySelector("h3");
    if (heading && this._config.title) heading.textContent = this._config.title;
    const sub = this.querySelector(".hph-subtitle");
    if (sub && this._config.subtitle) sub.textContent = this._config.subtitle;
    if (this._config.button) {
      const btn = this.querySelector("button");
      if (btn) btn.title = this._config.title || "Help";
    }
  }

  set hass(_hass) {
    /* not used — pure-presentation card */
  }

  getCardSize() {
    return 1;
  }

  _render() {
    if (this._rendered) return;
    this._rendered = true;

    // Subtle ? circle, sized to align with adjacent heading text.
    // Wrapped in ha-card only so horizontal-stack layout stays predictable;
    // the card chrome is suppressed via transparent background and no shadow.
    this.style.display = "block";

    const card = document.createElement("ha-card");
    card.style.cssText = `
      display: flex; align-items: center; justify-content: flex-start;
      gap: 8px;
      padding: 8px 16px;
      min-height: 0;
      background: transparent;
      box-shadow: none;
      border: none;
    `;

    this._titleRow = null;
    if (this._config.heading) {
      const headWrap = document.createElement("div");
      headWrap.style.cssText = "display:flex; flex-direction:column; gap:2px; flex:1;";
      const titleRow = document.createElement("div");
      titleRow.style.cssText = "display:flex; align-items:center; gap:8px;";
      const h = document.createElement("h3");
      h.textContent = this._config.title;
      h.style.cssText = `
        margin: 0;
        font-size: 1.05em;
        font-weight: 500;
        color: var(--primary-text-color, inherit);
      `;
      titleRow.appendChild(h);
      headWrap.appendChild(titleRow);
      if (this._config.subtitle) {
        const sub = document.createElement("div");
        sub.className = "hph-subtitle";
        sub.textContent = this._config.subtitle;
        sub.style.cssText = `
          font-size: 0.85em;
          color: var(--secondary-text-color, #8a8a8a);
        `;
        headWrap.appendChild(sub);
      }
      this._titleRow = titleRow;
      card.appendChild(headWrap);
    }

    const btn = document.createElement("button");
    btn.type = "button";
    btn.title = this._config.title;
    btn.setAttribute("aria-label", `Help: ${this._config.title}`);
    btn.textContent = this._config.label || "?";
    btn.style.cssText = `
      cursor: pointer;
      background: transparent;
      color: var(--secondary-text-color, #8a8a8a);
      border: 1px solid var(--divider-color, #cfcfcf);
      border-radius: 50%;
      width: 22px; height: 22px;
      padding: 0;
      font-size: 0.85em;
      font-weight: 600;
      line-height: 1;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      transition: color 120ms ease, border-color 120ms ease, background 120ms ease;
    `;

    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      this._openModal();
    });
    btn.addEventListener("mouseenter", () => {
      btn.style.color = "var(--primary-color, #03a9f4)";
      btn.style.borderColor = "var(--primary-color, #03a9f4)";
      btn.style.background = "var(--secondary-background-color, rgba(0,0,0,0.04))";
    });
    btn.addEventListener("mouseleave", () => {
      btn.style.color = "var(--secondary-text-color, #8a8a8a)";
      btn.style.borderColor = "var(--divider-color, #cfcfcf)";
      btn.style.background = "transparent";
    });

    if (this._config.button) {
      (this._titleRow || card).appendChild(btn);
    }
    this.appendChild(card);
  }

  _openModal() {
    if (this._modal) return;

    const overlay = document.createElement("div");
    overlay.style.cssText = `
      position: fixed; inset: 0;
      background: rgba(0, 0, 0, 0.45);
      z-index: 9999;
      display: flex; align-items: center; justify-content: center;
      padding: 16px;
      animation: hph-help-fade-in 120ms ease-out;
    `;

    const panel = document.createElement("div");
    panel.style.cssText = `
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color, #000);
      max-width: 640px; width: 100%;
      max-height: 80vh; overflow-y: auto;
      padding: 20px 24px;
      border-radius: 12px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
    `;
    panel.addEventListener("click", (e) => e.stopPropagation());

    const header = document.createElement("div");
    header.style.cssText = `
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--divider-color, #e0e0e0);
    `;

    const titleEl = document.createElement("h2");
    titleEl.textContent = this._config.title;
    titleEl.style.cssText = "margin: 0; font-size: 1.15em; font-weight: 500;";

    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.title = "Close";
    closeBtn.textContent = "✕";
    closeBtn.style.cssText = `
      cursor: pointer;
      background: transparent;
      border: none;
      color: var(--secondary-text-color, #666);
      font-size: 1.4em;
      line-height: 1;
      padding: 4px 8px;
      border-radius: 4px;
    `;
    closeBtn.addEventListener("mouseenter", () => {
      closeBtn.style.background = "var(--divider-color, #e0e0e0)";
    });
    closeBtn.addEventListener("mouseleave", () => {
      closeBtn.style.background = "transparent";
    });

    header.appendChild(titleEl);
    header.appendChild(closeBtn);

    const body = document.createElement("ha-markdown");
    body.content = this._config.content;
    body.breaks = true;

    panel.appendChild(header);
    panel.appendChild(body);
    overlay.appendChild(panel);
    document.body.appendChild(overlay);
    this._modal = overlay;

    const close = () => this._closeModal();
    overlay.addEventListener("click", close);
    closeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      close();
    });
    this._escHandler = (e) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("keydown", this._escHandler);
  }

  _closeModal() {
    if (this._modal) {
      this._modal.remove();
      this._modal = null;
    }
    if (this._escHandler) {
      document.removeEventListener("keydown", this._escHandler);
      this._escHandler = null;
    }
  }

  disconnectedCallback() {
    this._closeModal();
  }
}

if (!customElements.get("hph-help")) {
  customElements.define("hph-help", HphHelpCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.find((c) => c.type === "hph-help")) {
  window.customCards.push({
    type: "hph-help",
    name: "HPH Help",
    description: "Inline help popup for HeatPump Hero dashboards",
  });
}

// ──────────────────────────────────────────────────────────────────────────
// <hph-tile> — language-following value tile (mushroom-like look).
// Renders a colored icon + a value (from an entity, formatted) + a translated
// secondary label (from help_<lang>.json via label_key). Solves the problem
// that mushroom-template-card text is server-rendered and can't follow the
// per-user UI language.
//
//   - type: custom:hph-tile
//     entity: sensor.hph_cop_daily
//     label_key: kpi_cop_today        # secondary label, per-user language
//     decimals: 2
//     icon: mdi:calendar-today
//     color_thresholds: [[3.5,"green"],[2.5,"amber"],[0.0001,"red"]]
//     color_else: grey
//     navigate: /hph/efficiency        # or more_info: true
// ──────────────────────────────────────────────────────────────────────────
const __HPH_COLORS = {
  green: "#43a047", amber: "#ffa726", orange: "#fb8c00", red: "#e53935",
  grey: "#78909c", blue: "#2196f3", "light-blue": "#03a9f4", cyan: "#00bcd4",
  teal: "#009688", yellow: "#fdd835", "deep-orange": "#ff7043",
  "blue-grey": "#78909c", purple: "#ab47bc",
};
function __hphColor(name) {
  return __HPH_COLORS[name] || name || "var(--secondary-text-color)";
}

class HphTileCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.entity) throw new Error("hph-tile: 'entity' required");
    this._cfg = {
      entity: config.entity,
      label_key: config.label_key || null,
      label: config.label || "",
      decimals: config.decimals,
      suffix: config.suffix || "",
      use_unit: config.use_unit !== false,
      icon: config.icon || "mdi:gauge",
      icon_color: config.icon_color || null,
      color_thresholds: config.color_thresholds || null,
      color_else: config.color_else || "grey",
      navigate: config.navigate || null,
      more_info: config.more_info === true,
    };
    this._built = false;
    this._render();
    if (this._cfg.label_key) {
      this._resolveLabel().then(() => this._update()).catch(() => {});
    }
  }

  async _resolveLabel() {
    const lang = __hphCurrentLang();
    let strings = await __hphLoadHelpStrings(lang);
    let entry = strings[this._cfg.label_key];
    if (!entry && lang !== "en") {
      strings = await __hphLoadHelpStrings("en");
      entry = strings[this._cfg.label_key];
    }
    if (entry && entry.title) this._cfg.label = entry.title;
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  getCardSize() { return 1; }

  _color(value) {
    if (this._cfg.icon_color) return __hphColor(this._cfg.icon_color);
    if (this._cfg.color_thresholds && value !== null && !isNaN(value)) {
      for (const [min, col] of this._cfg.color_thresholds) {
        if (value >= min) return __hphColor(col);
      }
    }
    return __hphColor(this._cfg.color_else);
  }

  _render() {
    if (this._built) return;
    this._built = true;
    this.style.display = "block";
    const card = document.createElement("ha-card");
    card.style.cssText =
      "display:flex; align-items:center; gap:12px; padding:12px 16px; height:100%; box-sizing:border-box;";
    const iconWrap = document.createElement("div");
    iconWrap.className = "hph-tile-iconwrap";
    iconWrap.style.cssText =
      "flex:0 0 auto; width:40px; height:40px; border-radius:50%; display:flex; align-items:center; justify-content:center;";
    const icon = document.createElement("ha-icon");
    icon.setAttribute("icon", this._cfg.icon);
    icon.className = "hph-tile-icon";
    iconWrap.appendChild(icon);
    const textWrap = document.createElement("div");
    textWrap.style.cssText = "display:flex; flex-direction:column; min-width:0;";
    const primary = document.createElement("span");
    primary.className = "hph-tile-primary";
    primary.style.cssText =
      "font-size:1.05em; font-weight:600; color:var(--primary-text-color); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;";
    const secondary = document.createElement("span");
    secondary.className = "hph-tile-secondary";
    secondary.style.cssText =
      "font-size:0.85em; color:var(--secondary-text-color); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;";
    secondary.textContent = this._cfg.label || "";
    textWrap.appendChild(primary);
    textWrap.appendChild(secondary);
    card.appendChild(iconWrap);
    card.appendChild(textWrap);
    if (this._cfg.navigate || this._cfg.more_info) {
      card.style.cursor = "pointer";
      card.addEventListener("click", () => this._onTap());
    }
    this.appendChild(card);
    this._els = { primary, secondary, iconWrap, icon };
  }

  _onTap() {
    if (this._cfg.navigate) {
      history.pushState(null, "", this._cfg.navigate);
      window.dispatchEvent(new CustomEvent("location-changed"));
    } else if (this._cfg.more_info) {
      this.dispatchEvent(new CustomEvent("hass-more-info", {
        bubbles: true, composed: true, detail: { entityId: this._cfg.entity },
      }));
    }
  }

  _update() {
    if (!this._els) return;
    const st = this._hass && this._hass.states[this._cfg.entity];
    let valNum = null, text = "—";
    if (st && st.state !== "unavailable" && st.state !== "unknown") {
      valNum = parseFloat(st.state);
      if (!isNaN(valNum)) {
        const dec = this._cfg.decimals;
        text = dec === undefined ? String(st.state) : valNum.toFixed(dec);
      } else {
        text = st.state;
      }
      if (this._cfg.suffix) text += this._cfg.suffix;
      else if (this._cfg.use_unit && st.attributes && st.attributes.unit_of_measurement) {
        text += " " + st.attributes.unit_of_measurement;
      }
    }
    this._els.primary.textContent = text;
    if (this._cfg.label) this._els.secondary.textContent = this._cfg.label;
    const col = this._color(valNum);
    this._els.icon.style.color = col;
    this._els.iconWrap.style.background = col + "22"; // ~13% alpha tint
  }
}

if (!customElements.get("hph-tile")) {
  customElements.define("hph-tile", HphTileCard);
}
window.customCards = window.customCards || [];
if (!window.customCards.find((c) => c.type === "hph-tile")) {
  window.customCards.push({
    type: "hph-tile",
    name: "HPH Tile",
    description: "Language-following value tile for HeatPump Hero dashboards",
  });
}

console.info(
  "%c HPH-HELP %c loaded ",
  "color: white; background: #0277bd; padding: 2px 6px; border-radius: 3px;",
  "color: #0277bd;"
);

})(); // end IIFE
