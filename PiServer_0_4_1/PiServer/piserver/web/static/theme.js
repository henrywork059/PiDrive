(() => {
  const themeClasses = ['theme-ops-flat'];
  const settingsStorageKey = 'PiServerStyleSettings:v0_4_1';
  const legacyOverrideKeys = [
    'PiServerStyleSettings:v0_4_0',
    'PiServerStyleCustom:v0_3_5',
    'PiServerStyleCustom:v0_3_4',
    'PiServerStyleCustom:v0_3_3'
  ];

  const defaultSettings = {
    fontScale: 80,
    gridGap: 4,
    workspacePad: 10,
    panelPad: 12,
    panelHeadPad: 10,
    controlGap: 8,
    sectionGap: 12,
    cardGap: 10,
    fieldGap: 10,
    radius: 10,
    controlRadius: 12,
    cardRadius: 14,
    bg: '#1b1d23',
    panel: '#232630',
    panelAlt: '#2a2e39',
    text: '#f1f2f7',
    muted: '#9ea5b5',
    accent: '#f4a31e',
    danger: '#ca655d',
    ok: '#8d9d61',
    line: '#7a5d26',
    lineStrong: '#c28b2d'
  };

  const staticThemeVars = {
    '--warn': '#f4a31e',
    '--shadow': 'none'
  };

  const activeState = {
    theme: 'opsFlat',
    settings: null,
  };

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function normalizeNumber(value, fallback, min, max) {
    const num = Number(value);
    if (!Number.isFinite(num)) return fallback;
    return clamp(num, min, max);
  }

  function normalizeColor(value, fallback) {
    const raw = String(value || '').trim().toLowerCase();
    const hex = raw.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
    if (!hex) return fallback;
    if (hex[1].length === 3) {
      return '#' + [...hex[1]].map((char) => char + char).join('');
    }
    return '#' + hex[1];
  }

  function readStorage(key) {
    try {
      const raw = window.localStorage.getItem(key);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === 'object' ? parsed : null;
    } catch {
      return null;
    }
  }

  function rgbTripletFromHex(value) {
    const hex = normalizeColor(value, '#000000').slice(1);
    return [0, 2, 4].map((start) => parseInt(hex.slice(start, start + 2), 16)).join(', ');
  }

  function sanitizeSettings(input = {}) {
    return {
      fontScale: normalizeNumber(input.fontScale, defaultSettings.fontScale, 70, 135),
      gridGap: normalizeNumber(input.gridGap, defaultSettings.gridGap, 0, 24),
      workspacePad: normalizeNumber(input.workspacePad, defaultSettings.workspacePad, 0, 36),
      panelPad: normalizeNumber(input.panelPad, defaultSettings.panelPad, 4, 40),
      panelHeadPad: normalizeNumber(input.panelHeadPad, defaultSettings.panelHeadPad, 4, 32),
      controlGap: normalizeNumber(input.controlGap, defaultSettings.controlGap, 0, 24),
      sectionGap: normalizeNumber(input.sectionGap, defaultSettings.sectionGap, 0, 32),
      cardGap: normalizeNumber(input.cardGap, defaultSettings.cardGap, 0, 28),
      fieldGap: normalizeNumber(input.fieldGap, defaultSettings.fieldGap, 0, 28),
      radius: normalizeNumber(input.radius, defaultSettings.radius, 0, 36),
      controlRadius: normalizeNumber(input.controlRadius, defaultSettings.controlRadius, 0, 28),
      cardRadius: normalizeNumber(input.cardRadius, defaultSettings.cardRadius, 0, 28),
      bg: normalizeColor(input.bg, defaultSettings.bg),
      panel: normalizeColor(input.panel, defaultSettings.panel),
      panelAlt: normalizeColor(input.panelAlt, defaultSettings.panelAlt),
      text: normalizeColor(input.text, defaultSettings.text),
      muted: normalizeColor(input.muted, defaultSettings.muted),
      accent: normalizeColor(input.accent, defaultSettings.accent),
      danger: normalizeColor(input.danger, defaultSettings.danger),
      ok: normalizeColor(input.ok, defaultSettings.ok),
      line: normalizeColor(input.line, defaultSettings.line),
      lineStrong: normalizeColor(input.lineStrong, defaultSettings.lineStrong),
    };
  }

  function settingsToVars(settings) {
    const next = sanitizeSettings(settings);
    return {
      '--font-scale': `${next.fontScale}%`,
      '--font-scale-factor': String(next.fontScale / 100),
      '--gap': `${next.gridGap}px`,
      '--workspace-pad': `${next.workspacePad}px`,
      '--panel-pad': `${next.panelPad}px`,
      '--panel-head-pad-y': `${next.panelHeadPad}px`,
      '--panel-head-pad-x': `${next.panelHeadPad}px`,
      '--control-gap': `${next.controlGap}px`,
      '--section-gap': `${next.sectionGap}px`,
      '--card-gap': `${next.cardGap}px`,
      '--field-gap': `${next.fieldGap}px`,
      '--radius': `${next.radius}px`,
      '--control-radius': `${next.controlRadius}px`,
      '--card-radius': `${next.cardRadius}px`,
      '--bg': next.bg,
      '--panel': next.panel,
      '--panel-alt': next.panelAlt,
      '--text': next.text,
      '--muted': next.muted,
      '--accent': next.accent,
      '--accent-rgb': rgbTripletFromHex(next.accent),
      '--danger': next.danger,
      '--ok': next.ok,
      '--line': next.line,
      '--line-strong': next.lineStrong,
      ...staticThemeVars,
    };
  }

  function getDefaultSettings() {
    return { ...defaultSettings };
  }

  function migrateLegacySettings() {
    for (const key of legacyOverrideKeys) {
      const parsed = readStorage(key);
      if (!parsed) continue;
      const migrated = settingsFromOverrides(parsed);
      if (migrated) {
        try { window.localStorage.removeItem(key); } catch {}
        try { window.localStorage.setItem(settingsStorageKey, JSON.stringify(migrated)); } catch {}
        return migrated;
      }
    }
    return null;
  }

  function loadCustomSettings() {
    return readStorage(settingsStorageKey) || migrateLegacySettings() || null;
  }

  function saveCustomSettings(settings) {
    const clean = sanitizeSettings(settings);
    activeState.settings = clean;
    try {
      window.localStorage.setItem(settingsStorageKey, JSON.stringify(clean));
    } catch {}
    applyTheme(activeState.theme);
    return clean;
  }

  function clearCustomSettings() {
    activeState.settings = null;
    try { window.localStorage.removeItem(settingsStorageKey); } catch {}
    applyTheme(activeState.theme);
  }

  function applyVars(vars) {
    const root = document.documentElement;
    Object.entries(vars).forEach(([key, value]) => root.style.setProperty(key, value));
  }

  function applyCustomSettings(settings) {
    const clean = sanitizeSettings(settings);
    applyVars(settingsToVars(clean));
    return clean;
  }

  function applySavedSettings() {
    const saved = loadCustomSettings();
    activeState.settings = saved ? sanitizeSettings(saved) : null;
    applyTheme(activeState.theme);
    return { ...(activeState.settings || getDefaultSettings()) };
  }

  function getResolvedSettings() {
    return { ...getDefaultSettings(), ...(activeState.settings || {}) };
  }

  function getResolvedVars() {
    return settingsToVars(getResolvedSettings());
  }

  function settingsFromOverrides(overrides = {}) {
    if (!overrides || typeof overrides !== 'object') return null;
    const parseNumber = (key, fallback) => {
      const raw = String(overrides[key] || '');
      const match = raw.match(/-?\d+(?:\.\d+)?/);
      return match ? Number(match[0]) : fallback;
    };
    return sanitizeSettings({
      fontScale: parseNumber('--font-scale', defaultSettings.fontScale),
      gridGap: parseNumber('--gap', defaultSettings.gridGap),
      workspacePad: parseNumber('--workspace-pad', defaultSettings.workspacePad),
      panelPad: parseNumber('--panel-pad', defaultSettings.panelPad),
      panelHeadPad: parseNumber('--panel-head-pad-y', defaultSettings.panelHeadPad),
      controlGap: parseNumber('--control-gap', defaultSettings.controlGap),
      sectionGap: parseNumber('--section-gap', defaultSettings.sectionGap),
      cardGap: parseNumber('--card-gap', defaultSettings.cardGap),
      fieldGap: parseNumber('--field-gap', defaultSettings.fieldGap),
      radius: parseNumber('--radius', defaultSettings.radius),
      controlRadius: parseNumber('--control-radius', defaultSettings.controlRadius),
      cardRadius: parseNumber('--card-radius', defaultSettings.cardRadius),
      bg: overrides['--bg'],
      panel: overrides['--panel'],
      panelAlt: overrides['--panel-alt'],
      text: overrides['--text'],
      muted: overrides['--muted'],
      accent: overrides['--accent'],
      danger: overrides['--danger'],
      ok: overrides['--ok'],
      line: overrides['--line'],
      lineStrong: overrides['--line-strong'],
    });
  }

  function saveCustomOverrides(overrides = {}) {
    return saveCustomSettings(settingsFromOverrides(overrides) || getDefaultSettings());
  }

  function resetCustomOverrides() {
    clearCustomSettings();
    return getResolvedVars();
  }

  function getCustomOverrides() {
    return settingsToVars(activeState.settings || getDefaultSettings());
  }

  function applyTheme(name = 'opsFlat') {
    activeState.theme = 'opsFlat';
    document.documentElement.classList.remove(...themeClasses);
    document.documentElement.classList.add('theme-ops-flat');
    applyVars(settingsToVars(getResolvedSettings()));
    return activeState.theme;
  }

  window.PiServerStyle = {
    applyTheme,
    getCurrentTheme: () => activeState.theme,
    getDefaultSettings,
    getResolvedSettings,
    getResolvedVars,
    getCustomOverrides,
    loadCustomSettings,
    saveCustomSettings,
    clearCustomSettings,
    applyCustomSettings,
    applySavedSettings,
    saveCustomOverrides,
    resetCustomOverrides,
  };

  applySavedSettings();
})();
