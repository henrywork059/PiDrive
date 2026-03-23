(() => {
  const themeClasses = ['theme-ops-flat'];
  const storageKey = 'PiServerStyleCustom';
  const legacyStorageKeys = ['PiServerStyleCustom:v0_3_3', 'PiServerStyleCustom:v0_3_2'];
  const defaultThemeName = 'opsFlat';
  const themes = {
    opsFlat: {
      className: 'theme-ops-flat',
      vars: {
        '--bg': '#1b1d23',
        '--panel': '#232630',
        '--panel-alt': '#2a2e39',
        '--line': 'rgba(122, 93, 38, 0.34)',
        '--line-strong': 'rgba(194, 139, 45, 0.56)',
        '--text': '#f1f2f7',
        '--muted': '#9ea5b5',
        '--accent': '#f4a31e',
        '--accent-rgb': '244, 163, 30',
        '--danger': '#ca655d',
        '--warn': '#f4a31e',
        '--ok': '#8d9d61',
        '--shadow': 'none',
        '--gap': '4px',
        '--radius': '10px',
        '--workspace-pad': '10px',
        '--panel-pad': '12px',
        '--panel-head-pad-y': '10px',
        '--panel-head-pad-x': '12px',
        '--control-gap': '8px',
        '--section-gap': '12px',
        '--card-gap': '8px',
        '--field-gap': '7px',
        '--font-scale': '82%',
        '--tight-gap': '6px',
        '--card-pad': '8px'
      }
    }
  };

  function normalizeHex(value, fallback) {
    const raw = String(value || '').trim();
    if (/^#[0-9a-fA-F]{6}$/.test(raw)) return raw.toLowerCase();
    return fallback;
  }

  function hexToRgbString(hex) {
    const value = normalizeHex(hex, '#000000').slice(1);
    return `${parseInt(value.slice(0, 2), 16)}, ${parseInt(value.slice(2, 4), 16)}, ${parseInt(value.slice(4, 6), 16)}`;
  }

  function withAlpha(hex, alpha, fallback) {
    const base = normalizeHex(hex, fallback || '#000000');
    const value = base.slice(1);
    const r = parseInt(value.slice(0, 2), 16);
    const g = parseInt(value.slice(2, 4), 16);
    const b = parseInt(value.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  function px(value, fallback) {
    const n = Number(value);
    return `${Number.isFinite(n) ? n : fallback}px`;
  }

  function pct(value, fallback) {
    const n = Number(value);
    return `${Number.isFinite(n) ? n : fallback}%`;
  }

  function setVars(vars) {
    const root = document.documentElement;
    Object.entries(vars || {}).forEach(([key, value]) => root.style.setProperty(key, value));
  }

  function buildCustomVars(settings = {}) {
    const defaults = themes[defaultThemeName].vars;
    const accent = normalizeHex(settings.accent, defaults['--accent']);
    return {
      '--bg': normalizeHex(settings.bg, defaults['--bg']),
      '--panel': normalizeHex(settings.panel, defaults['--panel']),
      '--panel-alt': normalizeHex(settings.panelAlt, defaults['--panel-alt']),
      '--text': normalizeHex(settings.text, defaults['--text']),
      '--muted': normalizeHex(settings.muted, defaults['--muted']),
      '--accent': accent,
      '--accent-rgb': hexToRgbString(accent),
      '--danger': normalizeHex(settings.danger, defaults['--danger']),
      '--warn': accent,
      '--ok': normalizeHex(settings.ok, defaults['--ok']),
      '--line': withAlpha(settings.line, 0.34, '#7a5d26'),
      '--line-strong': withAlpha(settings.lineStrong, 0.56, '#c28b2d'),
      '--shadow': defaults['--shadow'],
      '--gap': px(settings.gridGap, 4),
      '--radius': px(settings.radius, 10),
      '--workspace-pad': px(settings.workspacePad, 10),
      '--panel-pad': px(settings.panelPad, 12),
      '--panel-head-pad-y': px(settings.panelHeadPad, 10),
      '--panel-head-pad-x': px(settings.panelHeadPadX ?? 12, 12),
      '--control-gap': px(settings.controlGap, 8),
      '--section-gap': px(settings.sectionGap, 12),
      '--card-gap': px(settings.cardGap, 8),
      '--field-gap': px(settings.fieldGap, 7),
      '--font-scale': pct(settings.fontScale, 82),
      '--tight-gap': px(settings.controlGap, 8),
      '--card-pad': px(Math.max(6, Number(settings.panelPad) - 4 || 8), 8),
    };
  }

  function applyTheme(name = defaultThemeName) {
    const theme = themes[name] || themes[defaultThemeName];
    setVars(theme.vars);
    document.documentElement.classList.remove(...themeClasses);
    if (theme.className) document.documentElement.classList.add(theme.className);
    return name in themes ? name : defaultThemeName;
  }

  function parseStoredSettings(raw) {
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : null;
  }

  function loadCustomSettings() {
    try {
      const primary = parseStoredSettings(localStorage.getItem(storageKey));
      if (primary) return primary;
      for (const legacyKey of legacyStorageKeys) {
        const legacy = parseStoredSettings(localStorage.getItem(legacyKey));
        if (legacy) {
          localStorage.setItem(storageKey, JSON.stringify(legacy));
          return legacy;
        }
      }
      return null;
    } catch {
      return null;
    }
  }

  function saveCustomSettings(settings) {
    localStorage.setItem(storageKey, JSON.stringify(settings || {}));
  }

  function clearCustomSettings() {
    try { localStorage.removeItem(storageKey); } catch {}
  }

  function applyCustomSettings(settings) {
    applyTheme(defaultThemeName);
    setVars(buildCustomVars(settings));
    return settings;
  }

  function applySavedSettings() {
    const saved = loadCustomSettings();
    if (saved) applyCustomSettings(saved);
    else applyTheme(defaultThemeName);
  }

  window.PiServerStyle = {
    themes,
    storageKey,
    buildCustomVars,
    applyTheme,
    applyCustomSettings,
    applySavedSettings,
    loadCustomSettings,
    saveCustomSettings,
    clearCustomSettings,
    getDefaultSettings: () => ({
      bg: themes[defaultThemeName].vars['--bg'],
      panel: themes[defaultThemeName].vars['--panel'],
      panelAlt: themes[defaultThemeName].vars['--panel-alt'],
      text: themes[defaultThemeName].vars['--text'],
      muted: themes[defaultThemeName].vars['--muted'],
      accent: themes[defaultThemeName].vars['--accent'],
      danger: themes[defaultThemeName].vars['--danger'],
      ok: themes[defaultThemeName].vars['--ok'],
      line: '#7a5d26',
      lineStrong: '#c28b2d',
      gridGap: 4,
      workspacePad: 10,
      panelPad: 12,
      panelHeadPad: 10,
      controlGap: 8,
      sectionGap: 12,
      cardGap: 8,
      fieldGap: 7,
      radius: 10,
      fontScale: 82,
    }),
  };

  applySavedSettings();
})();
