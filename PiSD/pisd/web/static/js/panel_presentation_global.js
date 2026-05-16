(() => {
  'use strict';

  const STORAGE_KEY = 'pisd.panelPresentation.v1';
  const SETTINGS_STORAGE_KEY = 'pisd.runtimeSettings.v2';
  const DEFAULTS = {
    theme: 'dark',
    layoutMode: 'auto',
    density: 'compact',
    fontScale: '1.0',
    panelGap: '10',
    panelRadius: '14',
    borderStrength: '1.0',
    shadowStrength: '0.20',
    minPanelWidth: '280',
    previewAspect: '16 / 9',
    previewFit: 'contain',
    panelPadding: '0.86',
    panelHeaderMode: 'compact',
    buttonScale: '0.92',
    consoleHeight: '180',
    cardAccent: 'subtle',
    autoSave: 'true',
  };

  function normalize(raw) {
    const source = raw && typeof raw === 'object' ? raw : {};
    return { ...DEFAULTS, ...source };
  }

  function readLocal() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return normalize(raw ? JSON.parse(raw) : DEFAULTS);
    } catch (_err) {
      return normalize(DEFAULTS);
    }
  }

  function readRuntimeLocal() {
    try { return JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY) || '{}') || {}; }
    catch (_err) { return {}; }
  }

  function save(settings) {
    const normalized = normalize(settings);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
    const runtime = readRuntimeLocal();
    runtime.panel_presentation = normalized;
    runtime.saved_at = new Date().toISOString();
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(runtime));
    return normalized;
  }

  function aspectToCss(value) {
    return String(value || DEFAULTS.previewAspect).replace('/', ' / ');
  }

  function apply(input) {
    const settings = normalize(input || readLocal());
    const body = document.body;
    if (body) {
      body.dataset.pisdTheme = settings.theme;
      body.dataset.pisdLayout = settings.layoutMode;
      body.dataset.pisdDensity = settings.density;
      body.dataset.pisdPanelHeader = settings.panelHeaderMode;
      body.dataset.pisdCardAccent = settings.cardAccent;
    }
    const root = document.documentElement;
    root.style.setProperty('--pisd-ui-font-scale', settings.fontScale);
    root.style.setProperty('--pisd-ui-gap', `${Number(settings.panelGap || DEFAULTS.panelGap)}px`);
    root.style.setProperty('--pisd-ui-radius', `${Number(settings.panelRadius || DEFAULTS.panelRadius)}px`);
    root.style.setProperty('--pisd-ui-border-alpha', settings.borderStrength);
    root.style.setProperty('--pisd-ui-shadow-alpha', settings.shadowStrength);
    root.style.setProperty('--pisd-ui-panel-min-width', `${Number(settings.minPanelWidth || DEFAULTS.minPanelWidth)}px`);
    root.style.setProperty('--pisd-ui-preview-aspect', aspectToCss(settings.previewAspect));
    root.style.setProperty('--pisd-ui-preview-fit', String(settings.previewFit || DEFAULTS.previewFit));
    root.style.setProperty('--pisd-ui-density-pad', String(settings.panelPadding || DEFAULTS.panelPadding));
    root.style.setProperty('--pisd-ui-button-scale', String(settings.buttonScale || DEFAULTS.buttonScale));
    root.style.setProperty('--pisd-ui-console-height', `${Number(settings.consoleHeight || DEFAULTS.consoleHeight)}px`);
    window.dispatchEvent(new CustomEvent('pisd:presentation-applied', { detail: settings }));
    return settings;
  }

  async function loadFromBackend() {
    try {
      const response = await fetch('/api/settings', { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      const panel = payload?.settings?.panel_presentation;
      if (panel && typeof panel === 'object') {
        const normalized = save(panel);
        apply(normalized);
        return normalized;
      }
    } catch (_err) {
      // Keep UI usable if the backend settings endpoint is unavailable.
    }
    const runtime = readRuntimeLocal();
    const fallback = runtime.panel_presentation || readLocal();
    return apply(fallback);
  }

  window.PiSDPanelPresentation = { STORAGE_KEY, SETTINGS_STORAGE_KEY, DEFAULTS, normalize, read: readLocal, save, apply, loadFromBackend };

  document.addEventListener('DOMContentLoaded', () => {
    apply(readLocal());
    loadFromBackend();
  });
  window.addEventListener('storage', event => {
    if (event.key === STORAGE_KEY || event.key === SETTINGS_STORAGE_KEY) loadFromBackend();
  });
})();
