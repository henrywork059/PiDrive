(() => {
  const themeClasses = ['theme-ops-flat'];
  const styleStorageKey = 'PiServerStyleCustom:v0_3_2';
  const themes = {
    opsFlat: {
      className: 'theme-ops-flat',
      vars: {
        '--bg': '#1b1d23',
        '--panel': '#232630',
        '--panel-alt': '#2a2e39',
        '--line': '#6f5930',
        '--line-strong': '#b38132',
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
        '--page-margin': '10px',
        '--panel-padding': '14px',
        '--control-font-size': '0.92rem',
        '--base-font-size': '80%'
      }
    }
  };

  let currentTheme = 'opsFlat';

  function setVars(vars) {
    const root = document.documentElement;
    Object.entries(vars || {}).forEach(([key, value]) => root.style.setProperty(key, value));
  }

  function sanitizeStyle(input = {}) {
    const fallback = themes.opsFlat.vars;
    const val = (k) => String(input[k] ?? fallback[k]).trim() || fallback[k];
    return {
      '--bg': val('--bg'),
      '--panel': val('--panel'),
      '--panel-alt': val('--panel-alt'),
      '--line': val('--line'),
      '--line-strong': val('--line-strong') || val('--line'),
      '--text': val('--text'),
      '--muted': val('--muted'),
      '--accent': val('--accent'),
      '--danger': val('--danger'),
      '--warn': val('--warn'),
      '--ok': val('--ok'),
      '--gap': clampPx(val('--gap'), 0, 30, fallback['--gap']),
      '--radius': clampPx(val('--radius'), 0, 36, fallback['--radius']),
      '--page-margin': clampPx(val('--page-margin'), 0, 40, fallback['--page-margin']),
      '--panel-padding': clampPx(val('--panel-padding'), 4, 40, fallback['--panel-padding']),
      '--control-font-size': clampRem(val('--control-font-size'), 0.7, 1.4, fallback['--control-font-size']),
      '--base-font-size': clampPercent(val('--base-font-size'), 60, 140, fallback['--base-font-size']),
      '--shadow': val('--shadow'),
      '--accent-rgb': hexToRgb(val('--accent'), fallback['--accent-rgb'])
    };
  }

  function clampPx(raw, min, max, fallback) {
    const n = Number.parseFloat(raw);
    if (!Number.isFinite(n)) return fallback;
    return `${Math.min(max, Math.max(min, n))}px`;
  }

  function clampRem(raw, min, max, fallback) {
    const n = Number.parseFloat(raw);
    if (!Number.isFinite(n)) return fallback;
    return `${Math.min(max, Math.max(min, n)).toFixed(2)}rem`;
  }

  function clampPercent(raw, min, max, fallback) {
    const n = Number.parseFloat(raw);
    if (!Number.isFinite(n)) return fallback;
    return `${Math.min(max, Math.max(min, n))}%`;
  }

  function hexToRgb(color, fallback = '244, 163, 30') {
    const value = String(color || '').trim();
    const match = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(value);
    if (!match) return fallback;
    return `${parseInt(match[1], 16)}, ${parseInt(match[2], 16)}, ${parseInt(match[3], 16)}`;
  }

  function getSavedStyle() {
    try {
      const raw = localStorage.getItem(styleStorageKey);
      if (!raw) return null;
      return sanitizeStyle(JSON.parse(raw));
    } catch {
      return null;
    }
  }

  function saveCustomStyle(style) {
    const clean = sanitizeStyle(style);
    localStorage.setItem(styleStorageKey, JSON.stringify(clean));
    return clean;
  }

  function clearCustomStyle() {
    try { localStorage.removeItem(styleStorageKey); } catch {}
  }

  function applyTheme(name = 'opsFlat') {
    const theme = themes[name] || themes.opsFlat;
    currentTheme = name in themes ? name : 'opsFlat';
    setVars(theme.vars);
    const saved = getSavedStyle();
    if (saved) setVars(saved);
    document.documentElement.classList.remove(...themeClasses);
    if (theme.className) document.documentElement.classList.add(theme.className);
    return currentTheme;
  }

  window.PiServerStyle = {
    themes,
    applyTheme,
    getCurrentTheme: () => currentTheme,
    getSavedStyle,
    saveCustomStyle,
    clearCustomStyle,
    sanitizeStyle,
  };

  applyTheme('opsFlat');
})();
