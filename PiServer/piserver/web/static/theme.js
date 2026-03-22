(() => {
  const themeClasses = ['theme-ops-flat'];
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
        '--radius': '10px'
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
