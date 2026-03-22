(() => {
  const themeClasses = ['theme-ops-grid', 'theme-ops-flat'];
  const themes = {
    opsGrid: {
      className: 'theme-ops-grid',
      vars: {
        '--bg': '#0b1013',
        '--panel': 'rgba(17, 23, 28, 0.96)',
        '--panel-alt': 'rgba(13, 19, 23, 0.96)',
        '--line': 'rgba(118, 139, 146, 0.16)',
        '--line-strong': 'rgba(72, 214, 201, 0.26)',
        '--text': '#edf4f4',
        '--muted': '#8d9ea4',
        '--accent': '#3dd4cb',
        '--danger': '#cf6d60',
        '--warn': '#cfa469',
        '--ok': '#7cad98',
        '--shadow': '0 18px 36px rgba(0, 0, 0, 0.34)'
      }
    },
    opsFlat: {
      className: 'theme-ops-flat',
      vars: {
        '--bg': '#0f1316',
        '--panel': '#151b20',
        '--panel-alt': '#11171c',
        '--line': 'rgba(108, 121, 132, 0.28)',
        '--line-strong': 'rgba(135, 153, 166, 0.38)',
        '--text': '#d6dde3',
        '--muted': '#8e98a2',
        '--accent': '#5a8f96',
        '--danger': '#9a655d',
        '--warn': '#8e7a51',
        '--ok': '#6d8475',
        '--shadow': 'none',
        '--gap': '3px'
      }
    }
  };

  let currentTheme = 'opsFlat';

  function setVars(vars) {
    const root = document.documentElement;
    Object.entries(vars || {}).forEach(([key, value]) => root.style.setProperty(key, value));
  }

  function applyTheme(name = 'opsFlat') {
    const theme = themes[name] || themes.opsFlat;
    currentTheme = name in themes ? name : 'opsFlat';
    setVars(theme.vars);
    document.documentElement.classList.remove(...themeClasses);
    if (theme.className) document.documentElement.classList.add(theme.className);
    return currentTheme;
  }

  window.PiServerStyle = {
    themes,
    applyTheme,
    getCurrentTheme: () => currentTheme,
  };

  applyTheme('opsFlat');
})();
