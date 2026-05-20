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

// If the custom element is already registered (previous load of this script),
// bail out cleanly — re-registering would throw.
if (customElements.get("hph-help")) {
  console.info("[hph-help] already registered, skipping re-init");
  return;
}

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
      if (!this._config.content) this._config.content = entry.content || "";
    } else if (lang !== "en") {
      const en = await __hphLoadHelpStrings("en");
      const enEntry = en[this._config.translation_key];
      if (enEntry) {
        if (!this._config.title) this._config.title = enEntry.title || "";
        if (!this._config.content) this._config.content = enEntry.content || "";
      }
    }
    if (!this._config.title) this._config.title = "Help";
  }

  _updateTexts() {
    // Update inline heading text in-place after async translation resolution.
    const heading = this.querySelector("h3");
    if (heading && this._config.title) heading.textContent = this._config.title;
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

    if (this._config.heading) {
      const h = document.createElement("h3");
      h.textContent = this._config.title;
      h.style.cssText = `
        margin: 0;
        font-size: 1.05em;
        font-weight: 500;
        color: var(--primary-text-color, inherit);
      `;
      card.appendChild(h);
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
      card.appendChild(btn);
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

customElements.define("hph-help", HphHelpCard);

window.customCards = window.customCards || [];
if (!window.customCards.find((c) => c.type === "hph-help")) {
  window.customCards.push({
    type: "hph-help",
    name: "HPH Help",
    description: "Inline help popup for HeatPump Hero dashboards",
  });
}

console.info(
  "%c HPH-HELP %c loaded ",
  "color: white; background: #0277bd; padding: 2px 6px; border-radius: 3px;",
  "color: #0277bd;"
);

})(); // end IIFE
