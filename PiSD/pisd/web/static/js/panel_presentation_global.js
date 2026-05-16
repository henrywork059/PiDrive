(() => {
  'use strict';

  const STORAGE_KEY = 'pisd.panelPresentation.v1';
  const DEFAULTS = {
    theme: 'dark',
    layoutMode: 'adaptive',
    density: 'compact',
    fontScale: '0.95',
    panelGap: '10',
    panelRadius: '14',
    borderStrength: '0.34',
    shadowStrength: '0.20',
    minPanelWidth: '280',
    previewAspect: '16/9',
    previewFit: 'contain',
    panelPadding: '0.85',
    panelHeaderMode: 'standard',
    buttonScale: '1.0',
    consoleHeight: '220',
    cardAccent: 'subtle',
    autoSave: 'true',
  };

  function normalize(raw) {
    const source = raw && typeof raw === 'object' ? raw : {};
    return { ...DEFAULTS, ...source };
  }

  function read() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return normalize(raw ? JSON.parse(raw) : DEFAULTS);
    } catch (_err) {
      return normalize(DEFAULTS);
    }
  }

  function save(settings) {
    const normalized = normalize(settings);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
    return normalized;
  }

  function aspectToCss(value) {
    return String(value || DEFAULTS.previewAspect).replace('/', ' / ');
  }

  function apply(input) {
    const settings = normalize(input || read());
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
    return settings;
  }

  window.PiSDPanelPresentation = { STORAGE_KEY, DEFAULTS, normalize, read, save, apply };

  document.addEventListener('DOMContentLoaded', () => apply(read()));
  window.addEventListener('storage', event => {
    if (event.key === STORAGE_KEY) apply(read());
  });
})();
