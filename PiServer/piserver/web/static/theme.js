(() => {
  const themeClasses = ['theme-ops-flat'];
  const customStyleKey = 'PiServerStyleCustom:v0_3_5';
  const selectedThemeKey = 'PiServerTheme:v1';
  const colorKeys = new Set(['--bg','--panel','--panel-alt','--line','--line-strong','--text','--muted','--accent','--accent-rgb','--danger','--warn','--ok']);
  const baseStyleVars = {
    '--font-scale': '80%',
    '--font-scale-factor': '0.8',
    '--workspace-pad': '10px',
    '--panel-pad': '12px',
    '--panel-head-pad-y': '10px',
    '--panel-head-pad-x': '12px',
    '--control-radius': '12px',
    '--card-radius': '14px',
    '--card-gap': '10px',
    '--field-gap': '10px'
  };
  const themes = {
    opsFlat: {
      className: 'theme-ops-flat',
      vars: {
        '--bg': '#1b1d23',
        '--panel': '#232630',
        '--panel-alt': '#2a2e39',
        '--line': 'rgba(255, 176, 44, 0.18)',
        '--line-strong': 'rgba(255, 176, 44, 0.34)',
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
        '--card-gap': '10px',
        '--field-gap': '10px'
      }
    }
  };

  // Keep historical presets and user-customized values separate.
  themes.obsidian = { className: 'theme-ops-flat', vars: {...themes.opsFlat.vars, ...{"--bg":"#14171C","--panel":"#20252D","--panel-alt":"#292F39","--line":"#363F4B","--line-strong":"#64748B","--text":"#EDF1F7","--muted":"#A5AFBF","--accent":"#6495FF","--accent-rgb":"100, 149, 255","--danger":"#B91C2C","--warn":"#FDE68A","--ok":"#86EFAC","--vd-on-accent":"#14171C","--vd-success-bg":"#20362A","--vd-warning-bg":"#3B321F","--vd-error-bg":"#42252C","--vd-error":"#FDA4AF","--vd-focus":"#FBBF24"}} };
  themes.light = { className: 'theme-ops-flat', vars: {...themes.opsFlat.vars, ...{"--bg":"#F4F6FA","--panel":"#FFFFFF","--panel-alt":"#E7EBF1","--line":"#CED5DF","--line-strong":"#64748B","--text":"#20252D","--muted":"#566171","--accent":"#315FD1","--accent-rgb":"49, 95, 209","--danger":"#B91C2C","--warn":"#92400E","--ok":"#166534","--vd-on-accent":"#FFFFFF","--vd-success-bg":"#E5F5E9","--vd-warning-bg":"#FFF1D6","--vd-error-bg":"#FCE8E8","--vd-error":"#B91C1C","--vd-focus":"#315FD1"}} };
  function themeKey(name) { return name === 'opsFlat' ? customStyleKey : customStyleKey + ':' + name; }
  function validTheme(name) { return Object.prototype.hasOwnProperty.call(themes, name); }
  function readSelectedTheme() {
    try { const name = window.localStorage.getItem(selectedThemeKey); return validTheme(name) ? name : 'opsFlat'; }
    catch { return 'opsFlat'; }
  }
  let currentTheme = readSelectedTheme();
  let customOverrides = withDerivedVars(loadCustomOverrides(currentTheme));

  function setVars(vars) {
    const root = document.documentElement;
    Object.entries(vars || {}).forEach(([key, value]) => root.style.setProperty(key, value));
  }

  function loadCustomOverrides(name = currentTheme) {
    try {
      const raw = window.localStorage.getItem(themeKey(name));
      if (!raw) return {};
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === 'object') return parsed;
      return {};
    } catch {
      return {};
    }
  }

  function withDerivedVars(vars = {}) {
    const next = { ...vars };
    const fontScale = String(next['--font-scale'] || '').match(/-?\d+(?:\.\d+)?/);
    if (fontScale) {
      next['--font-scale-factor'] = String(Number(fontScale[0]) / 100);
    }
    return next;
  }

  function saveCustomOverrides(vars = {}) {
    customOverrides = withDerivedVars(vars);
    try {
      if (Object.keys(customOverrides).length) {
        window.localStorage.setItem(themeKey(currentTheme), JSON.stringify(customOverrides));
      } else {
        window.localStorage.removeItem(themeKey(currentTheme));
      }
    } catch {}
    applyTheme(currentTheme);
    return getResolvedVars();
  }

  function resetCustomOverrides() {
    return saveCustomOverrides({});
  }

  function getResolvedVars(themeName = currentTheme) {
    const theme = themes[themeName] || themes.opsFlat;
    const inherited = themeName === 'opsFlat' ? {} : Object.fromEntries(Object.entries(loadCustomOverrides('opsFlat')).filter(([key]) => !colorKeys.has(key)));
    const own = themeName === currentTheme ? customOverrides : loadCustomOverrides(themeName);
    return { ...baseStyleVars, ...(theme.vars || {}), ...withDerivedVars(inherited), ...(own || {}) };
  }

  function applyTheme(name = 'opsFlat') {
    const next = validTheme(name) ? name : 'opsFlat';
    const theme = themes[next];
    if (next !== currentTheme) {
      currentTheme = next;
      customOverrides = withDerivedVars(loadCustomOverrides(next));
    }
    setVars(getResolvedVars());
    const root = document.documentElement;
    if (root.dataset) root.dataset.pidriveTheme = currentTheme;
    if (root.style && 'colorScheme' in root.style) root.style.colorScheme = currentTheme === 'light' ? 'light' : 'dark';
    document.documentElement.classList.remove(...themeClasses);
    if (theme.className) document.documentElement.classList.add(theme.className);
    return currentTheme;
  }

  function saveSelectedTheme() {
    try { window.localStorage.setItem(selectedThemeKey, currentTheme); return true; }
    catch { return false; }
  }
  function restoreSelectedTheme() { return applyTheme(readSelectedTheme()); }

  window.PiServerStyle = {
    themes,
    applyTheme,
    saveSelectedTheme,
    restoreSelectedTheme,
    getCurrentTheme: () => currentTheme,
    getCustomOverrides: () => ({ ...(customOverrides || {}) }),
    getResolvedVars: () => getResolvedVars(),
    saveCustomOverrides,
    resetCustomOverrides,
  };

  applyTheme(currentTheme);
})();
