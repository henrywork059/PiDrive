(() => {
  'use strict';

  const STORAGE_KEY = 'pisd.panelPresentation.v1';
  const SETTINGS_STORAGE_KEY = 'pisd.runtimeSettings.v2';
  const DEFAULTS = {
    theme: 'dark',
    layoutMode: 'auto',
    layoutSystem: 'strict-responsive',
    semanticLayoutLock: 'true',
    previewPriority: 'fit-view',
    topbarMode: 'compact',
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
    adaptivePanels: 'true',
    statusPanelHWeight: '1',
    statusPanelVWeight: '1',
    previewPanelHWeight: '2',
    previewPanelVWeight: '2',
    controlPanelHWeight: '1',
    controlPanelVWeight: '1',
    settingsPanelHWeight: '1',
    settingsPanelVWeight: '1',
    logPanelHWeight: '2',
    logPanelVWeight: '1',
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
    try {
      const runtime = JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY) || '{}');
      return runtime && typeof runtime === 'object' && !Array.isArray(runtime) ? runtime : {};
    } catch (_err) { return {}; }
  }

  // Presentation synchronization is cache propagation, not a backend refresh.
  // Compare JSON values structurally so key ordering and unrelated runtime
  // timestamps cannot cause a new write or request.
  function equalValue(a, b) {
    if (a === b) return true;
    if (!a || !b || typeof a !== 'object' || typeof b !== 'object' || Array.isArray(a) !== Array.isArray(b)) return false;
    const keys = Object.keys(a);
    return keys.length === Object.keys(b).length && keys.every(key =>
      Object.prototype.hasOwnProperty.call(b, key) && equalValue(a[key], b[key]));
  }

  function panelValue(raw, runtime = false) {
    try {
      const parsed = JSON.parse(raw);
      const panel = runtime ? parsed?.panel_presentation : parsed;
      return panel && typeof panel === 'object' && !Array.isArray(panel) ? normalize(panel) : null;
    } catch (_err) { return null; }
  }

  let revision = 0;
  let pendingLoad = null;
  let synchronizedPanel = null;

  function cachedPanel(key) {
    try { return panelValue(localStorage.getItem(key), key === SETTINGS_STORAGE_KEY); }
    catch (_err) { return null; }
  }

  function readCurrent() {
    return normalize(cachedPanel(SETTINGS_STORAGE_KEY) || cachedPanel(STORAGE_KEY) || synchronizedPanel || readLocal());
  }

  function save(settings) {
    const normalized = normalize(settings);
    const panelChanged = !equalValue(cachedPanel(STORAGE_KEY), normalized);
    const runtimeChanged = !equalValue(cachedPanel(SETTINGS_STORAGE_KEY), normalized);
    if (panelChanged || runtimeChanged) revision += 1;
    if (panelChanged) localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
    if (runtimeChanged) {
      const runtime = readRuntimeLocal();
      runtime.panel_presentation = normalized;
      runtime.saved_at = new Date().toISOString();
      localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(runtime));
    }
    synchronizedPanel = normalize(normalized);
    return normalized;
  }

  function aspectToCss(value) {
    return String(value || DEFAULTS.previewAspect).replace('/', ' / ');
  }

  function spanValue(value, fallback = 1) {
    const number = Math.round(Number(value || fallback));
    if (!Number.isFinite(number)) return fallback;
    return Math.max(1, Math.min(4, number));
  }

  function applyPanelWeights(settings) {
    const roleMap = {
      status: ['statusPanelHWeight', 'statusPanelVWeight'],
      preview: ['previewPanelHWeight', 'previewPanelVWeight'],
      camera: ['previewPanelHWeight', 'previewPanelVWeight'],
      control: ['controlPanelHWeight', 'controlPanelVWeight'],
      drive: ['controlPanelHWeight', 'controlPanelVWeight'],
      settings: ['settingsPanelHWeight', 'settingsPanelVWeight'],
      log: ['logPanelHWeight', 'logPanelVWeight'],
    };
    document.querySelectorAll('[data-panel-role], .mdrv-panel, .md-panel, .st-card, .card, .pt-panel, .pp-card, .pp-preview-panel').forEach(panel => {
      const role = panel.dataset.panelRole || panel.dataset.panel || (panel.classList.contains('mdrv-preview-panel') ? 'preview' : panel.classList.contains('mdrv-status-panel') ? 'status' : panel.classList.contains('mdrv-log-panel') ? 'log' : panel.classList.contains('mdrv-drive-panel') || panel.classList.contains('mdrv-stop-panel') ? 'control' : panel.classList.contains('st-card') ? 'settings' : 'control');
      const keys = roleMap[role] || roleMap.control;
      panel.style.setProperty('--pisd-panel-h-span', spanValue(panel.dataset.panelHWeight || settings[keys[0]], 1));
      panel.style.setProperty('--pisd-panel-v-span', spanValue(panel.dataset.panelVWeight || settings[keys[1]], 1));
    });
  }

  function apply(input) {
    const settings = normalize(input || readCurrent());
    const body = document.body;
    if (body) {
      body.dataset.pisdTheme = settings.theme;
      body.dataset.pisdLayout = settings.layoutMode;
      body.dataset.pisdLayoutSystem = settings.layoutSystem || 'strict-responsive';
      body.dataset.pisdSemanticLayoutLock = String(settings.semanticLayoutLock) === 'false' ? 'false' : 'true';
      body.dataset.pisdPreviewPriority = settings.previewPriority || 'fit-view';
      body.dataset.pisdTopbarMode = settings.topbarMode || 'compact';
      body.dataset.pisdDensity = settings.density;
      body.dataset.pisdPanelHeader = settings.panelHeaderMode;
      body.dataset.pisdCardAccent = settings.cardAccent;
      body.dataset.pisdAdaptivePanels = String(settings.adaptivePanels) === 'false' ? 'false' : 'true';
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
    root.style.setProperty('--pisd-status-h-span', spanValue(settings.statusPanelHWeight, 1));
    root.style.setProperty('--pisd-status-v-span', spanValue(settings.statusPanelVWeight, 1));
    root.style.setProperty('--pisd-preview-h-span', spanValue(settings.previewPanelHWeight, 2));
    root.style.setProperty('--pisd-preview-v-span', spanValue(settings.previewPanelVWeight, 2));
    root.style.setProperty('--pisd-control-h-span', spanValue(settings.controlPanelHWeight, 1));
    root.style.setProperty('--pisd-control-v-span', spanValue(settings.controlPanelVWeight, 1));
    root.style.setProperty('--pisd-settings-h-span', spanValue(settings.settingsPanelHWeight, 1));
    root.style.setProperty('--pisd-settings-v-span', spanValue(settings.settingsPanelVWeight, 1));
    root.style.setProperty('--pisd-log-h-span', spanValue(settings.logPanelHWeight, 2));
    root.style.setProperty('--pisd-log-v-span', spanValue(settings.logPanelVWeight, 1));
    applyPanelWeights(settings);
    window.dispatchEvent(new CustomEvent('pisd:presentation-applied', { detail: settings }));
    return settings;
  }

  function loadFromBackend() {
    if (pendingLoad) return pendingLoad;
    const started = revision;
    const initialPanel = cachedPanel(STORAGE_KEY);
    const initialRuntime = cachedPanel(SETTINGS_STORAGE_KEY);
    const superseded = () => started !== revision ||
      !equalValue(initialPanel, cachedPanel(STORAGE_KEY)) ||
      !equalValue(initialRuntime, cachedPanel(SETTINGS_STORAGE_KEY));
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3500);
    pendingLoad = (async () => {
      try {
        const response = await fetch('/api/settings', { cache: 'no-store', signal: controller.signal });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const payload = await response.json();
        const panel = payload?.settings?.panel_presentation;
        if (panel && typeof panel === 'object' && !Array.isArray(panel)) {
          // A page-specific startup read may already have cached this exact
          // response. Allow that match, but never replace a newer different
          // presentation value with a delayed GET.
          if (superseded() && !equalValue(normalize(panel), readCurrent())) return readCurrent();
          const normalized = save(panel);
          apply(normalized);
          return normalized;
        }
      } catch (_err) {
        // Keep UI usable if the backend settings endpoint is unavailable.
      }
      if (superseded()) return readCurrent();
      const fallback = cachedPanel(SETTINGS_STORAGE_KEY) || readLocal();
      synchronizedPanel = fallback;
      return apply(fallback);
    })().finally(() => { clearTimeout(timeout); pendingLoad = null; });
    return pendingLoad;
  }

  window.PiSDPanelPresentation = { STORAGE_KEY, SETTINGS_STORAGE_KEY, DEFAULTS, normalize, read: readCurrent, save, apply, loadFromBackend };

  document.addEventListener('DOMContentLoaded', () => {
    synchronizedPanel = readCurrent();
    apply(synchronizedPanel);
    loadFromBackend();
  });
  window.addEventListener('storage', event => {
    if (event.key !== STORAGE_KEY && event.key !== SETTINGS_STORAGE_KEY) return;
    if (event.storageArea && event.storageArea !== localStorage) return;
    const isRuntime = event.key === SETTINGS_STORAGE_KEY;
    const previous = panelValue(event.oldValue, isRuntime);
    const next = panelValue(event.newValue, isRuntime);
    // Ignore manual-drive/config-only updates, deleted/invalid caches and
    // queued events whose value has already been replaced by a later write.
    if (!next || equalValue(previous, next) || !equalValue(next, cachedPanel(event.key))) return;
    // The full runtime cache is also written by real page-specific settings
    // loaders. Do not let a delayed dedicated-cache event replace it.
    const runtimePanel = cachedPanel(SETTINGS_STORAGE_KEY);
    if (!isRuntime && runtimePanel && !equalValue(next, runtimePanel)) return;
    revision += 1;
    if (!equalValue(synchronizedPanel, next)) {
      synchronizedPanel = next;
      apply(next);
    }
    // Remote notifications never write storage or call GET /api/settings.
  });
})();
